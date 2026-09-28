import secrets
from typing import Annotated

from fastapi import Header

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

settings = get_settings()


async def require_admin_key(
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> None:
    if x_admin_key is None or not secrets.compare_digest(
        x_admin_key,
        settings.admin_api_key,
    ):
        raise AuthenticationError("invalid admin api key")


async def require_callback_key(
    x_callback_key: Annotated[str | None, Header(alias="X-Callback-Key")] = None,
) -> None:
    if x_callback_key is None or not secrets.compare_digest(
        x_callback_key,
        settings.callback_api_key,
    ):
        raise AuthenticationError("invalid callback api key")
