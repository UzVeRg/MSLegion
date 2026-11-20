from typing import Annotated

from fastapi import APIRouter, Depends, Response, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.exceptions import error_responses
from app.modules.auth import service
from app.modules.auth.exceptions import InvalidSessionError, TelegramLoginUnavailableError
from app.modules.auth.schemas import SessionToken, TelegramLogin
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"], responses=error_responses(401))
session_bearer = HTTPBearer(scheme_name="UserSession", auto_error=False)
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


async def require_session_token_hash(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(session_bearer)],
) -> bytes:
    if credentials is None:
        raise InvalidSessionError
    return service.hash_session_token(credentials.credentials)


TokenHash = Annotated[bytes, Depends(require_session_token_hash)]


@router.post(
    "/telegram",
    summary="Войти через Telegram",
    responses=error_responses(403, 422, 503),
)
async def login_with_telegram(
    payload: TelegramLogin,
    response: Response,
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionToken:
    if settings.telegram_bot_token is None:
        raise TelegramLoginUnavailableError
    result = await service.login_with_telegram(
        session, payload.init_data, bot_token=settings.telegram_bot_token.get_secret_value()
    )
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/me", response_model=UserRead, summary="Получить собственный профиль")
async def get_own_profile(
    response: Response, token_hash: TokenHash, session: SessionDependency
) -> User:
    user = await service.get_own_profile(session, token_hash)
    response.headers["Cache-Control"] = "no-store"
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Отозвать текущую сессию")
async def logout(token_hash: TokenHash, session: SessionDependency) -> None:
    await service.logout(session, token_hash)
