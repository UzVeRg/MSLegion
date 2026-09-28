import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.users.schemas import UserCreate


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    user = User(
        telegram_id=payload.telegram_id,
        display_name=payload.display_name,
    )
    session.add(user)
    return user


async def get_user_by_id(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> User | None:
    statement: Select[tuple[User]] = select(User).where(User.id == user_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
) -> User | None:
    statement: Select[tuple[User]] = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def list_users(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 50,
) -> list[User]:
    statement: Select[tuple[User]] = (
        select(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def count_users(session: AsyncSession) -> int:
    statement = select(func.count()).select_from(User)
    result = await session.execute(statement)
    return int(result.scalar_one())
