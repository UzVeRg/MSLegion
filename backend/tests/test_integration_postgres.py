import asyncio
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.core.security as security_module
from app.core.config import get_settings
from app.core.database import Base, get_session
from app.main import app
from app.modules.integrations.models import IntegrationEvent
from app.modules.users.models import User

settings = get_settings()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not settings.run_integration_tests,
        reason="integration tests are disabled",
    ),
]


async def run_http_flow_with_real_postgres(
    monkeypatch,
) -> None:
    engine = create_async_engine(
        settings.test_database_url,
        pool_pre_ping=True,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

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
    app.dependency_overrides[get_session] = override_session

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            user_response = await client.post(
                "/api/v1/users",
                json={
                    "telegram_id": 987654321,
                    "display_name": "Integration User",
                },
            )
            assert user_response.status_code == 201

            first_callback = await client.post(
                "/api/v1/callbacks/events",
                headers={
                    "X-Callback-Key": "integration-callback",
                },
                json={
                    "source": "integration-test",
                    "event_id": "event-1",
                    "event_type": "ping",
                    "payload": {"value": 1},
                },
            )
            assert first_callback.status_code == 200
            assert first_callback.json()["duplicate"] is False

            duplicate_callback = await client.post(
                "/api/v1/callbacks/events",
                headers={
                    "X-Callback-Key": "integration-callback",
                },
                json={
                    "source": "integration-test",
                    "event_id": "event-1",
                    "event_type": "ping",
                    "payload": {"value": 1},
                },
            )
            assert duplicate_callback.status_code == 200
            assert duplicate_callback.json()["duplicate"] is True

            users_response = await client.get("/api/v1/users")
            assert users_response.status_code == 200
            assert len(users_response.json()) == 1

            events_response = await client.get(
                "/api/v1/admin/callbacks",
                headers={
                    "X-Admin-Key": "integration-admin",
                },
            )
            assert events_response.status_code == 200
            assert len(events_response.json()) == 1
    finally:
        app.dependency_overrides.clear()

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

        await engine.dispose()


def test_http_flow_with_real_postgres(
    monkeypatch,
) -> None:
    asyncio.run(
        run_http_flow_with_real_postgres(monkeypatch),
        loop_factory=asyncio.SelectorEventLoop,
    )
