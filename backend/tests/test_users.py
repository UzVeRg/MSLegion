from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

import app.modules.users.router as users_router_module
from app.core.database import get_session
from app.main import app
from app.modules.users.service import (
    UserNotFoundError,
    UserTelegramIdConflictError,
)


class DummySession:
    pass


async def override_session() -> AsyncIterator[DummySession]:
    yield DummySession()


def build_user(
    *,
    user_id: UUID | None = None,
    telegram_id: int | None = 123456789,
    display_name: str = "Test User",
) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=user_id or uuid4(),
        telegram_id=telegram_id,
        display_name=display_name,
        status="active",
        created_at=now,
        updated_at=now,
    )


def test_create_user_returns_201(monkeypatch) -> None:
    created = build_user()

    async def fake_create_user(session, payload):
        assert isinstance(session, DummySession)
        assert payload.display_name == "Test User"
        return created

    monkeypatch.setattr(
        users_router_module.user_service,
        "create_user",
        fake_create_user,
    )
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/users",
                json={
                    "telegram_id": 123456789,
                    "display_name": "  Test User  ",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["id"] == str(created.id)
    assert response.json()["display_name"] == "Test User"


def test_create_user_returns_409_for_duplicate_telegram_id(monkeypatch) -> None:
    async def fake_create_user(session, payload):
        raise UserTelegramIdConflictError

    monkeypatch.setattr(
        users_router_module.user_service,
        "create_user",
        fake_create_user,
    )
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/users",
                json={
                    "telegram_id": 123456789,
                    "display_name": "Duplicate",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409


def test_get_user_returns_200(monkeypatch) -> None:
    user_id = uuid4()
    existing = build_user(user_id=user_id)

    async def fake_get_user(session, requested_user_id):
        assert requested_user_id == user_id
        return existing

    monkeypatch.setattr(
        users_router_module.user_service,
        "get_user",
        fake_get_user,
    )
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/users/{user_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == str(user_id)


def test_get_user_returns_404(monkeypatch) -> None:
    async def fake_get_user(session, requested_user_id):
        raise UserNotFoundError

    monkeypatch.setattr(
        users_router_module.user_service,
        "get_user",
        fake_get_user,
    )
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/users/{uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_list_users_returns_200(monkeypatch) -> None:
    users = [
        build_user(display_name="First"),
        build_user(telegram_id=None, display_name="Second"),
    ]

    async def fake_list_users(session, *, offset, limit):
        assert offset == 0
        assert limit == 50
        return users

    monkeypatch.setattr(
        users_router_module.user_service,
        "list_users",
        fake_list_users,
    )
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/users")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()) == 2
