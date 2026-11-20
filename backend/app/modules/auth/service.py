import re
import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth import repository
from app.modules.auth.exceptions import InvalidSessionError, UserAccessDisabledError
from app.modules.auth.models import UserSession
from app.modules.auth.schemas import SessionToken
from app.modules.auth.telegram import TelegramIdentity, verify_telegram_init_data
from app.modules.users import repository as users_repository
from app.modules.users.exceptions import UserTelegramUnconfirmedError
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate

SESSION_TTL = timedelta(hours=8)
SESSION_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")


async def _resolve_telegram_user(session: AsyncSession, identity: TelegramIdentity) -> User:
    payload = UserCreate(telegram_id=identity.telegram_id, display_name=identity.display_name)
    user = await users_repository.insert_user(session, payload, telegram_verified=True)
    if user is None:
        # Отдельный запрос видит запись после завершения конкурирующей вставки.
        user = await users_repository.get_user_by_telegram_id(session, identity.telegram_id)
        if user is None or not user.telegram_verified:
            raise UserTelegramUnconfirmedError
    return user


async def resolve_telegram_user_id(
    session: AsyncSession,
    init_data: str,
    *,
    bot_token: str,
    now: int,
) -> UUID:
    identity = verify_telegram_init_data(init_data, bot_token=bot_token, now=now)
    async with session.begin():
        user = await _resolve_telegram_user(session, identity)
        user_id = user.id
    return user_id


async def login_with_telegram(
    session: AsyncSession, init_data: str, *, bot_token: str
) -> SessionToken:
    now = datetime.now(UTC)
    identity = verify_telegram_init_data(init_data, bot_token=bot_token, now=int(now.timestamp()))
    async with session.begin():
        user = await _resolve_telegram_user(session, identity)
        if user.status != "active":
            raise UserAccessDisabledError
        token = secrets.token_urlsafe(32)
        expires_at = now + SESSION_TTL
        session.add(
            UserSession(
                token_hash=sha256(token.encode()).digest(),
                user_id=user.id,
                expires_at=expires_at,
            )
        )
    return SessionToken(access_token=token, expires_at=expires_at)


def hash_session_token(token: str) -> bytes:
    if not SESSION_TOKEN_PATTERN.fullmatch(token):
        raise InvalidSessionError
    return sha256(token.encode()).digest()


async def get_own_profile(session: AsyncSession, token_hash: bytes) -> User:
    user = await repository.get_session_owner(session, token_hash, datetime.now(UTC))
    if user is None:
        raise InvalidSessionError
    return user


async def logout(session: AsyncSession, token_hash: bytes) -> None:
    async with session.begin():
        if not await repository.revoke_session(session, token_hash, datetime.now(UTC)):
            raise InvalidSessionError
