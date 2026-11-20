from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.database import get_session
from app.main import app


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/users"),
        ("GET", f"/api/v1/users/{uuid4()}"),
        ("POST", "/api/v1/users"),
    ],
)
async def test_user_management_requires_admin(method, path, monkeypatch, client):
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: None)
    response = await client.request(method, path, json={"display_name": "Test"})
    assert response.status_code == 401


def test_unconfigured_and_legacy_keys_disable_access(monkeypatch):
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.delenv("CALLBACK_API_KEY", raising=False)
    defaults = Settings(_env_file=None)
    legacy = Settings(
        _env_file=None, admin_api_key="change-me", callback_api_key="change-me-callback"
    )
    for settings in (defaults, legacy):
        assert not settings.admin_api_key
        assert not settings.callback_api_key


def test_admin_and_callback_keys_must_differ():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, admin_api_key="same-test-key", callback_api_key="same-test-key")
