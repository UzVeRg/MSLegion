import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import get_session
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_api_key", "test-admin")
    monkeypatch.setattr(get_settings(), "callback_api_key", "test-callback")
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: None)
    with TestClient(
        app, headers={"X-Admin-Key": "test-admin", "X-Callback-Key": "test-callback"}
    ) as client:
        yield client


@pytest.mark.parametrize(
    "body",
    [
        {"display_name": "Test", "telegram_id": 2**63},
        {"display_name": "bad\x00name"},
    ],
)
def test_unstorable_user_returns_validation_error(client, body):
    assert client.post("/api/v1/users", json=body).status_code == 422


@pytest.mark.parametrize("payload", [{"bad\x00key": 1}, ["bad\x00value"]])
def test_unstorable_json_returns_validation_error(client, payload):
    event = {"source": "test", "event_id": "1", "event_type": "ping", "payload": payload}
    assert client.post("/api/v1/callbacks/events", json=event).status_code == 422


def test_validation_error_can_represent_nonfinite_input(client):
    response = client.post(
        "/api/v1/callbacks/events",
        content='{"source":"t","event_id":"1","event_type":"ping","payload":1e400}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["loc"] == ["body", "payload"]


def test_unpaired_surrogate_in_json_returns_validation_error(client):
    response = client.post(
        "/api/v1/callbacks/events",
        content=r'{"source":"t","event_id":"1","event_type":"ping","payload":["\ud800"]}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("path", ["/api/v1/users", "/api/v1/admin/callbacks"])
def test_offset_fits_database_integer(client, path):
    assert client.get(path, params={"offset": 2**63}).status_code == 422
