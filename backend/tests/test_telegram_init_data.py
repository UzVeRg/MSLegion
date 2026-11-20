import hmac
import json
from urllib.parse import urlencode

import pytest

from app.modules.auth.telegram import InvalidTelegramInitData, verify_telegram_init_data

BOT_TOKEN = "123456:test-token"
NOW = 1_700_000_000
USER = {"id": 4_500_000_000_001, "first_name": "Анна + Мария", "last_name": "Иванова"}


def signed_init_data(*, auth_date=NOW, user=USER):
    fields = {
        "user": json.dumps(user, ensure_ascii=False),
        "query_id": "query",
        "auth_date": str(auth_date),
        "signature": "third-party-signature",
    }
    signed_text = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.digest(b"WebAppData", BOT_TOKEN.encode(), "sha256")
    fields["hash"] = hmac.digest(secret, signed_text.encode(), "sha256").hex()
    return urlencode(fields)


def test_verifies_signed_identity():
    identity = verify_telegram_init_data(signed_init_data(), bot_token=BOT_TOKEN, now=NOW)

    assert identity.telegram_id == 4_500_000_000_001
    assert identity.display_name == "Анна + Мария Иванова"


@pytest.mark.parametrize("age", [300, -30])
def test_accepts_time_boundaries(age):
    data = signed_init_data(auth_date=NOW - age)
    assert verify_telegram_init_data(data, bot_token=BOT_TOKEN, now=NOW).telegram_id == USER["id"]


@pytest.mark.parametrize("age", [301, -31])
def test_rejects_stale_or_future_data(age):
    data = signed_init_data(auth_date=NOW - age)
    with pytest.raises(InvalidTelegramInitData):
        verify_telegram_init_data(data, bot_token=BOT_TOKEN, now=NOW)


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.replace("4500000000001", "4500000000002"),
        lambda data: data + "&%75ser=shadow",
        lambda data: data.split("&hash=")[0],
        lambda data: data.replace("&hash=", "&hash=%FF"),
        lambda data: data.replace("query_id=query", "query_id=query%0A"),
        lambda data: data.replace("query_id=query", "query_id=\ud800"),
    ],
)
def test_rejects_tampered_or_malformed_data(change):
    with pytest.raises(InvalidTelegramInitData):
        verify_telegram_init_data(change(signed_init_data()), bot_token=BOT_TOKEN, now=NOW)


def test_rejects_wrong_bot():
    with pytest.raises(InvalidTelegramInitData):
        verify_telegram_init_data(signed_init_data(), bot_token="other-token", now=NOW)


@pytest.mark.parametrize("telegram_id", [True, "123", 0, 2**63])
def test_rejects_invalid_signed_user_id(telegram_id):
    data = signed_init_data(user=USER | {"id": telegram_id})
    with pytest.raises(InvalidTelegramInitData):
        verify_telegram_init_data(data, bot_token=BOT_TOKEN, now=NOW)
