import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import get_settings

settings = get_settings()


async def require_admin_key(
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> None:
    if x_admin_key is None or not secrets.compare_digest(
        x_admin_key,
        settings.admin_api_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin api key",
        )


async def require_callback_key(
    x_callback_key: Annotated[str | None, Header(alias="X-Callback-Key")] = None,
) -> None:
    if x_callback_key is None or not secrets.compare_digest(
        x_callback_key,
        settings.callback_api_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid callback api key",
        )
