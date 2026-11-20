import secrets
from typing import Annotated

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

settings = get_settings()
admin_key_header = APIKeyHeader(name="X-Admin-Key", scheme_name="AdminKey", auto_error=False)
callback_key_header = APIKeyHeader(
    name="X-Callback-Key", scheme_name="CallbackKey", auto_error=False
)


def key_matches(provided: str | None, configured: str | None) -> bool:
    if not provided or not configured or not provided.isascii():
        return False
    return secrets.compare_digest(provided, configured)


async def require_admin_key(
    x_admin_key: Annotated[str | None, Security(admin_key_header)],
) -> None:
    if not key_matches(x_admin_key, settings.admin_api_key):
        raise AuthenticationError("Недействительный ключ API для администрирования")


async def require_callback_key(
    x_callback_key: Annotated[str | None, Security(callback_key_header)],
) -> None:
    if not key_matches(x_callback_key, settings.callback_api_key):
        raise AuthenticationError("Недействительный ключ API для приёма событий")
