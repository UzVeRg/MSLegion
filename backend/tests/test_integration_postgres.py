import asyncio
import base64
import hmac
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.schema import CreateSchema, DropSchema

import app.core.security as security_module
import app.modules.integrations.processing as integration_processing
from app.core.config import get_settings
from app.core.database import get_session
from app.main import app
from app.modules.auth.service import resolve_telegram_user_id
from app.modules.auth.telegram import InvalidTelegramInitData
from app.modules.users.exceptions import UserTelegramUnconfirmedError

settings = get_settings()
COMMUNITY_TEST_BOT_TOKEN = "123456:team-test"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not settings.run_integration_tests,
        reason="Интеграционные тесты отключены",
    ),
]


@asynccontextmanager
async def isolated_schema() -> AsyncIterator[AsyncEngine]:
    url = make_url(settings.test_database_url)
    working = make_url(settings.database_url)
    if not url.database or (url.host, url.port or 5432, url.database) == (
        working.host,
        working.port or 5432,
        working.database,
    ):
        raise ValueError("TEST_DATABASE_URL должен указывать на отдельную тестовую базу данных")

    schema = "mslegion_test_" + uuid4().hex
    engine = create_async_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        async with engine.begin() as connection:
            if await connection.scalar(text("SELECT current_database()")) != url.database:
                raise RuntimeError("Подключение установлено не к той базе данных")
            await connection.execute(CreateSchema(schema))
        try:
            yield engine
        finally:
            async with engine.begin() as connection:
                await connection.execute(DropSchema(schema, cascade=True))
    finally:
        await engine.dispose()


def migration_config(connection: Connection) -> Config:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


def migrate_and_check(connection: Connection) -> None:
    config = migration_config(connection)
    command.upgrade(config, "head")
    command.check(config)


def downgrade_to_base(connection: Connection) -> None:
    command.downgrade(migration_config(connection), "base")
    assert set(inspect(connection).get_table_names()).isdisjoint(
        {
            "users", "integration_events", "user_sessions", "communities",
            "community_memberships", "community_servers", "domain_events", "community_posts",
        }
    )


async def run_http_flow_with_real_postgres(monkeypatch, engine: AsyncEngine) -> None:
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    monkeypatch.setattr(
        security_module.settings,
        "admin_api_key",
        "integration-admin",
    )
    monkeypatch.setattr(
        security_module.settings,
        "callback_api_key",
        "integration-callback",
    )
    monkeypatch.setitem(app.dependency_overrides, get_session, override_session)

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        assert (await client.get("/ready")).status_code == 503
        admin_headers = {"X-Admin-Key": "integration-admin"}
        status = await client.get("/api/v1/admin/status", headers=admin_headers)
        assert status.json()["database"] == "unavailable"

        async with engine.begin() as connection:
            await connection.run_sync(migrate_and_check)

        assert (await client.get("/ready")).status_code == 200
        user = {"telegram_id": 987654321, "display_name": "Integration User"}
        responses = await asyncio.gather(
            *(client.post("/api/v1/users", headers=admin_headers, json=user) for _ in range(2))
        )
        assert sorted(response.status_code for response in responses) == [201, 409]

        callback_headers = {"X-Callback-Key": "integration-callback"}
        event = {
            "source": "integration-test",
            "event_id": "1",
            "event_type": "ping",
            "payload": {"value": 1},
        }
        path = "/api/v1/callbacks/events"
        receipts = await asyncio.gather(
            *(client.post(path, headers=callback_headers, json=event) for _ in range(2))
        )
        assert all(r.status_code == 200 for r in receipts)
        assert sorted(r.json()["duplicate"] for r in receipts) == [False, True]
        assert receipts[0].json()["event"]["id"] == receipts[1].json()["event"]["id"]

        for change in ({"event_type": "other"}, {"payload": {"value": True}}):
            conflict = await client.post(path, headers=callback_headers, json=event | change)
            assert conflict.status_code == 409
            assert conflict.json()["error"]["code"] == "event_id_conflict"

        users_response = await client.get(
            "/api/v1/users", headers={"X-Admin-Key": "integration-admin"}
        )
        assert users_response.status_code == 200
        assert len(users_response.json()) == 1

        events_response = await client.get(
            "/api/v1/admin/callbacks",
            headers={
                "X-Admin-Key": "integration-admin",
            },
        )
        assert events_response.status_code == 200
        assert [row["payload"] for row in events_response.json()] == [{"value": 1}]

        status = await client.get("/api/v1/admin/status", headers=admin_headers)
        assert status.status_code == 200
        assert status.json()["users"] == status.json()["integration_events"] == 1

        nullable = event | {"event_id": "nullable", "payload": None}
        for duplicate in (False, True):
            receipt = await client.post(path, headers=callback_headers, json=nullable)
            assert receipt.status_code == 200
            assert receipt.json()["duplicate"] is duplicate

        async with engine.begin() as connection:
            await connection.run_sync(downgrade_to_base)


def test_http_flow_with_real_postgres(
    monkeypatch,
) -> None:
    async def run():
        async with isolated_schema() as engine:
            await run_http_flow_with_real_postgres(monkeypatch, engine)

    asyncio.run(
        run(),
        loop_factory=asyncio.SelectorEventLoop,
    )


def signed_telegram_data(telegram_id: int, *, bot_token: str, now: int) -> str:
    user = json.dumps({"id": telegram_id, "first_name": "Анна"}, ensure_ascii=False)
    secret = hmac.digest(b"WebAppData", bot_token.encode(), "sha256")
    signature = hmac.digest(secret, f"auth_date={now}\nuser={user}".encode(), "sha256")
    return urlencode({"user": user, "auth_date": now, "hash": signature.hex()})


@asynccontextmanager
async def migrated_telegram_client(
    monkeypatch, *, legacy_status_event: bool = False
) -> AsyncIterator[AsyncClient]:
    async with isolated_schema() as engine:
        async with engine.begin() as connection:
            if legacy_status_event:
                await connection.run_sync(
                    lambda conn: command.upgrade(migration_config(conn), "20261120_0006")
                )
                await connection.execute(
                    text(
                        "INSERT INTO integration_events "
                        "(id, source, event_id, event_type, payload) "
                        "VALUES (:id, 'server-status', 'online', 'server.status', '{}')"
                    ),
                    {"id": uuid4()},
                )
            await connection.run_sync(migrate_and_check)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        async def override_session() -> AsyncIterator[AsyncSession]:
            async with factory() as session:
                yield session

        monkeypatch.setitem(app.dependency_overrides, get_session, override_session)
        monkeypatch.setitem(
            app.dependency_overrides,
            get_settings,
            lambda: settings.model_copy(
                update={"telegram_bot_token": SecretStr(COMMUNITY_TEST_BOT_TOKEN)}
            ),
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def login_for_community_test(
    client: AsyncClient, telegram_id: int
) -> tuple[dict[str, str], str]:
    data = signed_telegram_data(
        telegram_id, bot_token=COMMUNITY_TEST_BOT_TOKEN, now=int(datetime.now(UTC).timestamp())
    )
    response = await client.post("/api/v1/auth/telegram", json={"init_data": data})
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    profile = await client.get("/api/v1/auth/me", headers=headers)
    assert profile.status_code == 200
    return headers, profile.json()["id"]


def test_community_membership_with_real_postgres(monkeypatch) -> None:
    async def run() -> None:
        async with migrated_telegram_client(monkeypatch) as client:
            owner, owner_id = await login_for_community_test(client, 101)
            member, member_id = await login_for_community_test(client, 102)
            path = "/api/v1/communities"
            payload = {"name": "  Легион  "}
            assert (await client.post(path, json=payload)).status_code == 401
            created = await client.post(path, json=payload, headers=owner)
            assert created.status_code == 201
            community = created.json()
            assert community["name"] == "Легион"
            assert community["owner_id"] == owner_id

            detail = f"{path}/{community['id']}"
            members = f"{detail}/members"
            member_path = f"{members}/{member_id}"
            assert (await client.get(detail, headers=member)).status_code == 404
            assert (await client.get(path, headers=member)).json() == []
            assert (await client.get(path, headers=owner)).json() == [community]
            assert (await client.put(member_path, headers=member)).status_code == 404
            assert (await client.put(f"{members}/{uuid4()}", headers=owner)).status_code == 404
            added = await asyncio.gather(
                *(client.put(member_path, headers=owner) for _ in range(2))
            )
            assert [response.status_code for response in added] == [204, 204]
            assert (await client.get(members, headers=owner)).json() == [{"user_id": member_id}]
            assert (await client.get(members, headers=member)).status_code == 403
            assert (await client.get(detail, headers=member)).json() == community
            assert (await client.get(path, headers=member)).json() == [community]
            assert (await client.delete(member_path, headers=member)).status_code == 403
            assert (await client.delete(f"{members}/{owner_id}", headers=owner)).status_code == 409
            assert (await client.delete(member_path, headers=owner)).status_code == 204
            assert (await client.delete(member_path, headers=owner)).status_code == 204
            assert (await client.get(detail, headers=member)).status_code == 404
            assert (await client.get(path, headers=member)).json() == []

    asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)


def test_community_server_access_with_real_postgres(monkeypatch) -> None:
    async def run() -> None:
        async with migrated_telegram_client(monkeypatch) as client:
            owner, _ = await login_for_community_test(client, 201)
            member, member_id = await login_for_community_test(client, 202)
            outsider, _ = await login_for_community_test(client, 203)
            path = "/api/v1/communities"
            created = await client.post(path, json={"name": "Кластер"}, headers=owner)
            assert created.status_code == 201
            detail = f"{path}/{created.json()['id']}"
            member_path = f"{detail}/members/{member_id}"
            assert (await client.put(member_path, headers=owner)).status_code == 204

            servers = f"{detail}/servers"
            server = {"name": "Тестовый", "host": "Example.COM", "port": 27015}
            assert (await client.get(servers, headers=member)).json() == []
            assert (await client.get(servers, headers=outsider)).status_code == 404
            assert (await client.post(servers, headers=member, json=server)).status_code == 403
            assert (await client.post(servers, headers=outsider, json=server)).status_code == 404

            for changes in ({"host": "https://example.com"}, {"port": 65536}):
                invalid = await client.post(servers, headers=owner, json=server | changes)
                assert invalid.status_code == 422
            registered = await asyncio.gather(
                client.post(servers, headers=owner, json=server),
                client.post(servers, headers=owner, json=server | {"host": "example.com."}),
            )
            assert sorted(response.status_code for response in registered) == [201, 409]
            record = next(response.json() for response in registered if response.status_code == 201)
            assert record["host"] == "example.com"
            assert record["port"] == 27015
            assert record["community_id"] == created.json()["id"]
            assert (await client.get(servers, headers=member)).json() == [record]
            page = await client.get(servers, headers=member, params={"offset": 1})
            assert page.status_code == 200
            assert page.json() == []
            address = f"{servers}/{record['id']}"
            assert (await client.delete(address, headers=member)).status_code == 403
            assert (await client.delete(address, headers=outsider)).status_code == 404

            other = await client.post(path, headers=owner, json={"name": "Другой кластер"})
            assert other.status_code == 201
            wrong_community = f"{path}/{other.json()['id']}/servers/{record['id']}"
            assert (await client.delete(wrong_community, headers=owner)).status_code == 404
            assert (await client.get(servers, headers=owner)).json() == [record]

            assert (await client.delete(member_path, headers=owner)).status_code == 204
            assert (await client.get(servers, headers=member)).status_code == 404
            assert (await client.delete(address, headers=owner)).status_code == 204
            assert (await client.get(servers, headers=owner)).json() == []

    asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)


def test_server_status_event_processing_with_real_postgres(monkeypatch) -> None:
    async def run() -> None:
        async with migrated_telegram_client(monkeypatch, legacy_status_event=True) as client:
            owner, _ = await login_for_community_test(client, 401)
            monkeypatch.setattr(security_module.settings, "admin_api_key", "event-admin")
            monkeypatch.setattr(security_module.settings, "callback_api_key", "event-general")
            created = await client.post(
                "/api/v1/communities", headers=owner, json={"name": "Мониторинг"}
            )
            servers = f"/api/v1/communities/{created.json()['id']}/servers"
            stats_path = f"/api/v1/communities/{created.json()['id']}/statistics"
            outsider, _ = await login_for_community_test(client, 402)
            registered = await client.post(
                servers, headers=owner, json={"name": "Сервер", "host": "example.com", "port": 4444}
            )
            server_id = registered.json()["id"]
            incoming = "/api/v1/callbacks/server-status"
            generic = {"X-Callback-Key": "event-general"}
            admin = {"X-Admin-Key": "event-admin"}
            sender = {"X-Callback-Key": "event-status"}
            observed = datetime.now(UTC) - timedelta(minutes=1)
            payload = {
                "event_id": "online", "server_id": server_id,
                "online": True, "observed_at": observed.isoformat(),
            }
            assert (await client.post(incoming, headers=generic, json=payload)).status_code == 401
            monkeypatch.setattr(security_module.settings, "server_status_api_key", "event-status")
            generic_path = "/api/v1/callbacks/events"
            forged = {
                "source": "server-status", "event_id": "online",
                "event_type": "server.status", "payload": {},
            }
            wrong_source = await client.post(generic_path, headers=generic, json=forged)
            assert wrong_source.status_code == 403
            assert (await client.post(generic_path, headers=sender, json=forged)).status_code == 401
            receipt = await client.post(incoming, headers=sender, json=payload)
            duplicate = await client.post(incoming, headers=sender, json=payload)
            assert receipt.status_code == duplicate.status_code == 200
            assert receipt.json()["event"]["processing_state"] == "pending"
            assert duplicate.json()["duplicate"] is True
            assert (await client.get(servers, headers=owner)).json()[0]["online"] is None
            assert (await client.get(stats_path, headers=outsider)).status_code == 404
            stats = await client.get(stats_path, headers=owner)
            assert stats.status_code == 200
            assert stats.json() == {
                "members": 1, "servers": 1, "online": 0, "offline": 0, "unobserved": 1,
            }
            monitor = "/api/v1/admin/callbacks/processing"
            journal = "/api/v1/admin/domain-events"
            assert (await client.get(monitor, headers=owner)).status_code == 401
            assert (await client.get(journal, headers=owner)).status_code == 401
            metrics = (await client.get(monitor, headers=admin)).json()
            assert metrics["pending"] == 1
            assert metrics["oldest_pending_at"] is not None

            process = "/api/v1/admin/callbacks/process"
            assert (await client.post(process, headers=sender)).status_code == 401

            apply_status = integration_processing.apply_server_status

            async def fail_after_update(session, event):
                assert await apply_status(session, event) == "applied"
                await session.flush()
                raise RuntimeError("Имитированный сбой после обновления")

            with monkeypatch.context() as failure:
                failure.setattr(integration_processing, "apply_server_status", fail_after_update)
                failed = await client.post(process, headers=admin)
                assert failed.status_code == 500
            assert (await client.get(servers, headers=owner)).json()[0]["online"] is None
            history = await client.get("/api/v1/admin/callbacks", headers=admin)
            assert history.json()[0]["processing_state"] == "pending"
            before = (await client.get(journal, headers=admin)).json()
            assert [event["event_type"] for event in before] == [
                "community.server.registered", "community.created",
            ]

            results = await asyncio.gather(*(client.post(process, headers=admin) for _ in range(2)))
            assert all(response.status_code == 200 for response in results)
            assert sum(response.json()["applied"] for response in results) == 1
            assert (await client.get(servers, headers=owner)).json()[0]["online"] is True
            stats = (await client.get(stats_path, headers=owner)).json()
            assert stats["online"] == 1 and stats["unobserved"] == 0
            events = (await client.get(journal, headers=admin)).json()
            assert len(events) == 3
            assert events[0]["event_type"] == "community.server.status_observed"
            assert events[0]["subject_id"] == server_id
            assert events[0]["payload"]["online"] is True

            older = payload | {
                "event_id": "old-offline", "online": False,
                "observed_at": (observed - timedelta(seconds=1)).isoformat(),
            }
            invalid = payload | {"event_id": "unknown-server", "server_id": str(uuid4())}
            assert (await client.post(incoming, headers=sender, json=older)).status_code == 200
            assert (await client.post(incoming, headers=sender, json=invalid)).status_code == 200
            result = await client.post(process, headers=admin)
            assert result.json() == {"applied": 0, "ignored": 1, "rejected": 1}
            assert (await client.get(servers, headers=owner)).json()[0]["online"] is True
            result = await client.post(process, headers=admin)
            assert result.json() == {"applied": 0, "ignored": 0, "rejected": 0}
            assert (await client.get(journal, headers=admin)).json() == events
            assert (await client.get(monitor, headers=admin)).json() == {
                "pending": 0, "applied": 1, "ignored": 1, "rejected": 1,
                "oldest_pending_at": None,
            }

    asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)


def test_community_content_and_images_with_real_postgres(monkeypatch) -> None:
    async def run() -> None:
        async with migrated_telegram_client(monkeypatch) as client:
            owner, _ = await login_for_community_test(client, 501)
            member, member_id = await login_for_community_test(client, 502)
            outsider, _ = await login_for_community_test(client, 503)
            root = "/api/v1/communities"
            created = await client.post(root, headers=owner, json={"name": "Гайды"})
            assert created.status_code == 201
            detail = f"{root}/{created.json()['id']}"
            member_path = f"{detail}/members/{member_id}"
            assert (await client.put(member_path, headers=owner)).status_code == 204
            posts = f"{detail}/posts"
            document = {"title": "Первый гайд", "body": "Текст руководства"}
            assert (await client.get(posts, headers=outsider)).status_code == 404
            assert (await client.post(posts, headers=member, json=document)).status_code == 403

            async def oversized_post():
                yield b"x" * 131_072
                yield b"x"

            assert (await client.post(posts, content=oversized_post())).status_code == 401
            oversized = await client.post(posts, headers=owner, content=oversized_post())
            assert oversized.status_code == 413
            malformed = await client.post(posts, headers=owner, content=b"{")
            assert malformed.status_code == 422

            published = await client.post(posts, headers=owner, json=document)
            assert published.status_code == 201
            post = published.json()
            assert post["has_image"] is False
            activity_path = f"{detail}/statistics/activity"
            assert (await client.get(activity_path, headers=outsider)).status_code == 404
            activity = await client.get(activity_path, headers=member, params={"days": 2})
            assert activity.status_code == 200
            report = activity.json()
            assert datetime.fromisoformat(report["to_date"]) - datetime.fromisoformat(
                report["from_date"]
            ) == timedelta(days=1)
            assert {item["event_type"]: item["count"] for item in report["activity"]} == {
                "community.created": 1, "community.member.added": 1, "community.post.published": 1,
            }
            post_path = f"{posts}/{post['id']}"
            image_path = f"{post_path}/image"
            assert (await client.get(posts, headers=member)).json() == [post]
            assert (await client.get(image_path, headers=member)).status_code == 404

            png = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
                "/x8AAwMCAO+a1eAAAAAASUVORK5CYII="
            )
            assert (await client.put(image_path, headers=member, content=png)).status_code == 403
            unsupported = await client.put(image_path, headers=owner, content=b"<html>")
            assert unsupported.status_code == 415
            too_large = await client.put(image_path, headers=owner, content=b"x" * 2_097_153)
            assert too_large.status_code == 413
            assert (await client.put(image_path, headers=owner, content=png)).status_code == 204
            assert (await client.get(posts, headers=member)).json() == [post | {"has_image": True}]
            downloaded = await client.get(image_path, headers=member)
            assert downloaded.content == png
            assert downloaded.headers["content-type"] == "image/png"
            assert downloaded.headers["cache-control"] == "private, no-store"
            assert downloaded.headers["x-content-type-options"] == "nosniff"
            assert downloaded.headers["content-disposition"].startswith("attachment;")
            assert (await client.get(image_path, headers=outsider)).status_code == 404

            assert (await client.delete(member_path, headers=owner)).status_code == 204
            assert (await client.get(image_path, headers=member)).status_code == 404
            assert (await client.delete(post_path, headers=owner)).status_code == 204
            assert (await client.get(posts, headers=owner)).json() == []
            assert (await client.get(image_path, headers=owner)).status_code == 404

    asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)


def test_telegram_identity_binding_with_real_postgres(monkeypatch) -> None:
    legacy_id = uuid4()
    bot_token = "123456:integration-test"
    now = 1_700_000_000

    def init_data(telegram_id: int) -> str:
        return signed_telegram_data(telegram_id, bot_token=bot_token, now=now)

    async def run() -> None:
        async with isolated_schema() as engine:
            async with engine.begin() as connection:
                await connection.run_sync(
                    lambda conn: command.upgrade(migration_config(conn), "20260928_0002")
                )
                await connection.execute(
                    text(
                        "INSERT INTO users (id, telegram_id, display_name) "
                        "VALUES (:id, 10, :name)"
                    ),
                    {"id": legacy_id, "name": "Прежняя запись"},
                )
                await connection.run_sync(migrate_and_check)

            factory = async_sessionmaker(engine, expire_on_commit=False)

            async def login(data: str):
                async with factory() as session:
                    return await resolve_telegram_user_id(
                        session, data, bot_token=bot_token, now=now
                    )

            with pytest.raises(InvalidTelegramInitData):
                await login(init_data(20).replace("1700000000", "1700000001"))
            with pytest.raises(UserTelegramUnconfirmedError):
                await login(init_data(10))

            first, concurrent = await asyncio.gather(login(init_data(20)), login(init_data(20)))
            assert first == concurrent == await login(init_data(20))

            async def override_session() -> AsyncIterator[AsyncSession]:
                async with factory() as session:
                    yield session

            monkeypatch.setitem(app.dependency_overrides, get_session, override_session)
            monkeypatch.setattr(security_module.settings, "admin_api_key", "integration-admin")
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                path = f"/api/v1/users/{legacy_id}/telegram/confirmation"
                headers = {"X-Admin-Key": "integration-admin"}
                assert (await client.put(path, json={"telegram_id": 10})).status_code == 401
                mismatch = await client.put(path, json={"telegram_id": 11}, headers=headers)
                assert mismatch.status_code == 409
                with pytest.raises(UserTelegramUnconfirmedError):
                    await login(init_data(10))
                for _ in range(2):
                    confirmed = await client.put(path, json={"telegram_id": 10}, headers=headers)
                    assert confirmed.status_code == 204
                assert await login(init_data(10)) == legacy_id

                manual = await client.post(
                    "/api/v1/users",
                    headers=headers,
                    json={"telegram_id": 30, "display_name": "Ручная запись"},
                )
                assert manual.status_code == 201
                with pytest.raises(UserTelegramUnconfirmedError):
                    await login(init_data(30))

            async with factory() as session:
                rows = await session.execute(
                    text("SELECT telegram_id, display_name FROM users ORDER BY telegram_id")
                )
                assert rows.all() == [(10, "Прежняя запись"), (20, "Анна"), (30, "Ручная запись")]

    asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)


def test_telegram_sessions_with_real_postgres(monkeypatch) -> None:
    bot_token = "123456:session-test"

    async def run() -> None:
        async with isolated_schema() as engine:
            async with engine.begin() as connection:
                await connection.run_sync(migrate_and_check)
            factory = async_sessionmaker(engine, expire_on_commit=False)

            async def override_session() -> AsyncIterator[AsyncSession]:
                async with factory() as session:
                    yield session

            monkeypatch.setitem(app.dependency_overrides, get_session, override_session)
            monkeypatch.setitem(
                app.dependency_overrides,
                get_settings,
                lambda: settings.model_copy(update={"telegram_bot_token": SecretStr(bot_token)}),
            )
            monkeypatch.setattr(security_module.settings, "admin_api_key", "integration-admin")

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                login_path = "/api/v1/auth/telegram"
                profile_path = "/api/v1/auth/me"
                logout_path = "/api/v1/auth/logout"

                async def request_login(telegram_id: int, now: datetime):
                    init_data = signed_telegram_data(
                        telegram_id, bot_token=bot_token, now=int(now.timestamp())
                    )
                    return await client.post(login_path, json={"init_data": init_data})

                async def login(telegram_id: int) -> str:
                    now = datetime.now(UTC)
                    response = await request_login(telegram_id, now)
                    assert response.status_code == 200
                    assert response.headers["Cache-Control"] == "no-store"
                    body = response.json()
                    assert body["token_type"] == "bearer"
                    expires_at = datetime.fromisoformat(body["expires_at"])
                    assert now + timedelta(hours=8) <= expires_at
                    assert expires_at <= datetime.now(UTC) + timedelta(hours=8)
                    return body["access_token"]

                def bearer(token: str) -> dict[str, str]:
                    return {"Authorization": f"Bearer {token}"}

                invalid = await client.post(login_path, json={"init_data": "auth_date=1"})
                assert invalid.status_code == 401
                first_token = await login(101)
                second_token = await login(202)
                third_token = await login(101)
                assert len({first_token, second_token, third_token}) == 3

                first = await client.get(profile_path, headers=bearer(first_token))
                second = await client.get(profile_path, headers=bearer(second_token))
                third = await client.get(profile_path, headers=bearer(third_token))
                assert first.status_code == second.status_code == third.status_code == 200
                assert first.headers["Cache-Control"] == "no-store"
                assert first.json()["telegram_id"] == third.json()["telegram_id"] == 101
                assert first.json()["id"] == third.json()["id"]
                assert second.json()["telegram_id"] == 202
                assert first.json()["id"] != second.json()["id"]
                other_id = second.json()["id"]
                protected_routes = (
                    ("GET", "/api/v1/users", None),
                    ("POST", "/api/v1/users", {"display_name": "Проверка"}),
                    ("GET", f"/api/v1/users/{other_id}", None),
                    (
                        "PUT",
                        f"/api/v1/users/{other_id}/telegram/confirmation",
                        {"telegram_id": 202},
                    ),
                    ("GET", "/api/v1/admin/status", None),
                    ("GET", "/api/v1/admin/callbacks", None),
                    (
                        "POST",
                        "/api/v1/callbacks/events",
                        {"source": "test", "event_id": "deny-user-session", "event_type": "ping"},
                    ),
                )
                for method, path, payload in protected_routes:
                    denied = await client.request(
                        method, path, headers=bearer(first_token), json=payload
                    )
                    assert denied.status_code == 401, (method, path)

                async with engine.begin() as connection:
                    result = await connection.execute(text("SELECT token_hash FROM user_sessions"))
                    assert {bytes(row[0]) for row in result} == {
                        sha256(token.encode()).digest()
                        for token in (first_token, second_token, third_token)
                    }
                    await connection.execute(
                        text("UPDATE user_sessions SET expires_at = now() WHERE token_hash = :key"),
                        {"key": sha256(third_token.encode()).digest()},
                    )

                expired = await client.get(profile_path, headers=bearer(third_token))
                assert expired.status_code == 401
                assert expired.headers["WWW-Authenticate"] == "Bearer"
                logouts = await asyncio.gather(
                    *(client.post(logout_path, headers=bearer(first_token)) for _ in range(2))
                )
                assert sorted(response.status_code for response in logouts) == [204, 401]
                async with engine.connect() as connection:
                    revoked_at = await connection.scalar(
                        text("SELECT revoked_at FROM user_sessions WHERE token_hash = :key"),
                        {"key": sha256(first_token.encode()).digest()},
                    )
                    assert revoked_at is not None
                revoked_profile = await client.get(profile_path, headers=bearer(first_token))
                assert revoked_profile.status_code == 401
                other_profile = await client.get(profile_path, headers=bearer(second_token))
                assert other_profile.status_code == 200
                admin_profile = await client.get(
                    profile_path, headers={"X-Admin-Key": "integration-admin"}
                )
                assert admin_profile.status_code == 401

                async with engine.begin() as connection:
                    await connection.execute(
                        text("UPDATE users SET status = 'disabled' WHERE telegram_id = 202")
                    )
                blocked_profile = await client.get(profile_path, headers=bearer(second_token))
                assert blocked_profile.status_code == 401
                blocked_login = await request_login(202, datetime.now(UTC))
                assert blocked_login.status_code == 403

    asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)
