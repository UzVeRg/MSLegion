from unittest.mock import AsyncMock

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.main import app


async def test_health_returns_200(client) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


async def test_ready_returns_200_when_database_is_available(monkeypatch, client) -> None:
    session = AsyncMock(spec=AsyncSession)
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: session)

    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_ready_returns_503_when_database_is_unavailable(monkeypatch, client) -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = SQLAlchemyError()
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: session)

    response = await client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "http_error"
    assert body["error"]["message"] == "База данных недоступна"
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]
