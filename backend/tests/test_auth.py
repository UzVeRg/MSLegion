from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app


async def test_telegram_login_is_unavailable_without_a_bot_token(client, monkeypatch):
    monkeypatch.setitem(
        app.dependency_overrides,
        get_settings,
        lambda: Settings(_env_file=None, telegram_bot_token=""),
    )
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: None)

    response = await client.post("/api/v1/auth/telegram", json={"init_data": "auth_date=1"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "telegram_login_unavailable"


async def test_profile_rejects_malformed_bearer_before_accessing_database(client, monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: None)

    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_auth_openapi_requires_bearer_only_for_profile_and_logout():
    spec = app.openapi()
    assert spec["components"]["securitySchemes"]["UserSession"]["scheme"] == "bearer"
    paths = spec["paths"]
    assert not paths["/api/v1/auth/telegram"]["post"].get("security")
    assert paths["/api/v1/auth/me"]["get"]["security"] == [{"UserSession": []}]
    assert paths["/api/v1/auth/logout"]["post"]["security"] == [{"UserSession": []}]
