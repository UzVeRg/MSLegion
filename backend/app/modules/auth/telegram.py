import hmac
import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl

from app.core.exceptions import AppError
from app.core.validation import MAX_BIGINT

INIT_DATA_MAX_AGE_SECONDS = 300
INIT_DATA_CLOCK_SKEW_SECONDS = 30
INIT_DATA_MAX_LENGTH = 16_384


class InvalidTelegramInitData(AppError):
    status_code = 401
    code = "invalid_telegram_init_data"
    default_message = "Данные входа Telegram недействительны"


@dataclass(frozen=True, slots=True)
class TelegramIdentity:
    telegram_id: int
    display_name: str


def verify_telegram_init_data(init_data: str, *, bot_token: str, now: int) -> TelegramIdentity:
    if (
        not bot_token
        or len(init_data) > INIT_DATA_MAX_LENGTH
        or not init_data.isascii()
        or re.search(r"%(?![0-9A-Fa-f]{2})", init_data)
    ):
        raise InvalidTelegramInitData

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True, errors="strict")
    except ValueError:
        raise InvalidTelegramInitData from None
    fields = dict(pairs)
    if len(fields) != len(pairs) or any(
        not re.fullmatch(r"[a-zA-Z0-9_]+", key) or "\n" in value or "\r" in value
        for key, value in pairs
    ):
        raise InvalidTelegramInitData

    supplied_hash = fields.pop("hash", "")
    if not re.fullmatch(r"[0-9A-Fa-f]{64}", supplied_hash):
        raise InvalidTelegramInitData
    signed_text = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.digest(b"WebAppData", bot_token.encode(), "sha256")
    expected_hash = hmac.digest(secret, signed_text.encode(), "sha256")
    if not hmac.compare_digest(expected_hash, bytes.fromhex(supplied_hash)):
        raise InvalidTelegramInitData

    auth_date = fields.get("auth_date", "")
    if not re.fullmatch(r"[0-9]{1,12}", auth_date):
        raise InvalidTelegramInitData
    age = now - int(auth_date)
    if not -INIT_DATA_CLOCK_SKEW_SECONDS <= age <= INIT_DATA_MAX_AGE_SECONDS:
        raise InvalidTelegramInitData

    try:
        user = json.loads(fields.get("user", ""))
    except (ValueError, RecursionError):
        raise InvalidTelegramInitData from None
    if not isinstance(user, dict):
        raise InvalidTelegramInitData
    telegram_id = user.get("id")
    first_name = user.get("first_name")
    last_name = user.get("last_name", "")
    if (
        type(telegram_id) is not int
        or not 0 < telegram_id <= MAX_BIGINT
        or not isinstance(first_name, str)
        or not isinstance(last_name, str)
    ):
        raise InvalidTelegramInitData

    display_name = f"{first_name} {last_name}".strip()[:128].rstrip()
    if not display_name or "\x00" in display_name or re.search(r"[\ud800-\udfff]", display_name):
        raise InvalidTelegramInitData
    return TelegramIdentity(telegram_id=telegram_id, display_name=display_name)
