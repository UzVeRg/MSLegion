from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.main import app


def test_health_returns_200() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_ready_returns_200_when_database_is_available(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: session)

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_ready_returns_503_when_database_is_unavailable(monkeypatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = SQLAlchemyError()
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: session)

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "http_error"
    assert body["error"]["message"] == "database is unavailable"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
