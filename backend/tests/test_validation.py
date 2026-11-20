import pytest

from app.core.config import get_settings
from app.core.database import get_session
from app.main import app


@pytest.fixture
def authorized_client(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_api_key", "test-admin")
    monkeypatch.setattr(get_settings(), "callback_api_key", "test-callback")
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: None)
    client.headers.update({"X-Admin-Key": "test-admin", "X-Callback-Key": "test-callback"})
    return client


@pytest.mark.parametrize(
    "body",
    [
        {"display_name": "Test", "telegram_id": 2**63},
        {"display_name": "bad\x00name"},
    ],
)
async def test_unstorable_user_returns_validation_error(authorized_client, body):
    assert (await authorized_client.post("/api/v1/users", json=body)).status_code == 422


@pytest.mark.parametrize("payload", [{"bad\x00key": 1}, ["bad\x00value"]])
async def test_unstorable_json_returns_validation_error(authorized_client, payload):
    event = {"source": "test", "event_id": "1", "event_type": "ping", "payload": payload}
    assert (await authorized_client.post("/api/v1/callbacks/events", json=event)).status_code == 422


async def test_validation_error_can_represent_nonfinite_input(authorized_client):
    response = await authorized_client.post(
        "/api/v1/callbacks/events",
        content='{"source":"t","event_id":"1","event_type":"ping","payload":1e400}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["loc"] == ["body", "payload"]


async def test_unpaired_surrogate_in_json_returns_validation_error(authorized_client):
    response = await authorized_client.post(
        "/api/v1/callbacks/events",
        content=r'{"source":"t","event_id":"1","event_type":"ping","payload":["\ud800"]}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("path", ["/api/v1/users", "/api/v1/admin/callbacks"])
async def test_offset_fits_database_integer(authorized_client, path):
    assert (await authorized_client.get(path, params={"offset": 2**63})).status_code == 422
