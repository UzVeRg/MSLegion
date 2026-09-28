from fastapi.testclient import TestClient

import app.api.router as router_module
from app.main import app


def test_health_returns_200() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_200_when_database_is_available(monkeypatch) -> None:
    async def database_is_available() -> bool:
        return True

    monkeypatch.setattr(router_module, "check_database", database_is_available)

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_ready_returns_503_when_database_is_unavailable(monkeypatch) -> None:
    async def database_is_unavailable() -> bool:
        return False

    monkeypatch.setattr(router_module, "check_database", database_is_unavailable)

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "database is unavailable"}
