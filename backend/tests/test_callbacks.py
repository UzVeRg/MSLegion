from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

import app.core.security as security_module
import app.modules.integrations.router as integrations_router_module
from app.core.database import get_session
from app.main import app


class DummySession:
    pass


async def override_session() -> AsyncIterator[DummySession]:
    yield DummySession()


def build_event() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        source="test",
        event_id="event-1",
        event_type="ping",
        payload={"value": 1},
        received_at=datetime.now(UTC),
    )


def test_callback_returns_200(monkeypatch) -> None:
    event = build_event()

    async def fake_receive_event(session, payload):
        assert isinstance(session, DummySession)
        assert payload.source == "test"
        return event, False

    monkeypatch.setattr(
        integrations_router_module.service,
        "receive_event",
        fake_receive_event,
    )
    monkeypatch.setattr(
        security_module.settings,
        "callback_api_key",
        "callback-test",
    )
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/callbacks/events",
                headers={"X-Callback-Key": "callback-test"},
                json={
                    "source": "test",
                    "event_id": "event-1",
                    "event_type": "ping",
                    "payload": {"value": 1},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["duplicate"] is False


def test_duplicate_callback_returns_200(monkeypatch) -> None:
    event = build_event()

    async def fake_receive_event(session, payload):
        return event, True

    monkeypatch.setattr(
        integrations_router_module.service,
        "receive_event",
        fake_receive_event,
    )
    monkeypatch.setattr(
        security_module.settings,
        "callback_api_key",
        "callback-test",
    )
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/callbacks/events",
                headers={"X-Callback-Key": "callback-test"},
                json={
                    "source": "test",
                    "event_id": "event-1",
                    "event_type": "ping",
                    "payload": {"value": 1},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["duplicate"] is True


def test_callback_rejects_invalid_key(monkeypatch) -> None:
    monkeypatch.setattr(
        security_module.settings,
        "callback_api_key",
        "callback-test",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/callbacks/events",
            headers={"X-Callback-Key": "wrong"},
            json={
                "source": "test",
                "event_id": "event-1",
                "event_type": "ping",
                "payload": {"value": 1},
            },
        )

    assert response.status_code == 401


def test_admin_callback_history_returns_200(monkeypatch) -> None:
    events = [build_event()]

    async def fake_list_events(
        session,
        *,
        offset,
        limit,
        source,
        event_type,
    ):
        assert offset == 0
        assert limit == 50
        return events

    monkeypatch.setattr(
        integrations_router_module.service,
        "list_events",
        fake_list_events,
    )
    monkeypatch.setattr(
        security_module.settings,
        "admin_api_key",
        "admin-test",
    )
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/callbacks",
                headers={"X-Admin-Key": "admin-test"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()) == 1
