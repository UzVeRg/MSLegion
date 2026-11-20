import asyncio
import hmac
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
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
from app.core.config import get_settings
from app.core.database import get_session
from app.main import app
from app.modules.auth.service import resolve_telegram_user_id
from app.modules.auth.telegram import InvalidTelegramInitData
from app.modules.users.exceptions import UserTelegramUnconfirmedError

settings = get_settings()

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
    assert set(inspect(connection).get_table_names()).isdisjoint({"users", "integration_events"})


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


def test_telegram_identity_binding_with_real_postgres(monkeypatch) -> None:
    legacy_id = uuid4()
    bot_token = "123456:integration-test"
    now = 1_700_000_000

    def init_data(telegram_id: int) -> str:
        user = json.dumps({"id": telegram_id, "first_name": "Анна"}, ensure_ascii=False)
        secret = hmac.digest(b"WebAppData", bot_token.encode(), "sha256")
        signature = hmac.digest(secret, f"auth_date={now}\nuser={user}".encode(), "sha256")
        return urlencode({"user": user, "auth_date": now, "hash": signature.hex()})

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
