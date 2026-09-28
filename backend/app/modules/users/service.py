import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users import repository
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate


class UserNotFoundError(Exception):
    pass


class UserTelegramIdConflictError(Exception):
    pass


async def create_user(
    session: AsyncSession,
    payload: UserCreate,
) -> User:
    if payload.telegram_id is not None:
        existing = await repository.get_user_by_telegram_id(
            session,
            payload.telegram_id,
        )
        if existing is not None:
            raise UserTelegramIdConflictError

    user = await repository.create_user(session, payload)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise UserTelegramIdConflictError from exc

    await session.refresh(user)
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
