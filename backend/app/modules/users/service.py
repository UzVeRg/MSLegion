import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users import repository
from app.modules.users.exceptions import (
    UserNotFoundError,
    UserTelegramIdConflictError,
)
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate


async def create_user(
    session: AsyncSession,
    payload: UserCreate,
) -> User:
    async with session.begin():
        user = await repository.insert_user(session, payload)
        if user is None:
            raise UserTelegramIdConflictError
    return user


async def get_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> User:
    user = await repository.get_user_by_id(session, user_id)
    if user is None:
        raise UserNotFoundError
    return user


async def list_users(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 50,
) -> list[User]:
    return await repository.list_users(
        session,
        offset=offset,
        limit=limit,
    )
