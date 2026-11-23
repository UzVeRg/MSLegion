import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import app


async def test_public_faq_shares_configured_content_and_contacts(client):
    settings = Settings(
        support_faq={"ru": [{"question": "Что такое LC?", "answer": "Валюта MSLegion."}]},
        support_contacts={
            "telegram": "LegionHelp",
            "discord": "https://discord.gg/legion",
            "email": "help@example.org",
        },
        support_admin_ids={42},
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = await client.get("/api/v1/support?language=en")
    finally:
        app.dependency_overrides.pop(get_settings)

    assert response.status_code == 200
    assert response.json() == {
        "questions": [{"question": "Что такое LC?", "answer": "Валюта MSLegion."}],
        "contacts": [
            {"channel": "telegram", "label": "@LegionHelp", "url": "https://t.me/LegionHelp"},
            {
                "channel": "discord",
                "label": "https://discord.gg/legion",
                "url": "https://discord.gg/legion",
            },
            {"channel": "email", "label": "help@example.org", "url": "mailto:help@example.org"},
        ],
    }


@pytest.mark.parametrize("discord", [
    "javascript:alert(1)", "https://discord.gg.example.org/help", "https://discord.gg/help?x=1",
])
def test_rejects_invalid_discord_contact(discord):
    with pytest.raises(ValidationError):
        Settings(support_contacts={"discord": discord})
