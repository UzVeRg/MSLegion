from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import UserSession
from app.modules.users.models import User


async def make_room_for_session(
    session: AsyncSession, user_id: UUID, now: datetime, *, keep: int
) -> None:
    retained = (
        select(UserSession.token_hash)
        .where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .order_by(UserSession.expires_at.desc(), UserSession.token_hash.desc())
        .limit(keep)
    )
    await session.execute(
        delete(UserSession.__table__).where(
            UserSession.user_id == user_id, UserSession.token_hash.not_in(retained)
        )
    )


def _active_session_filters(token_hash: bytes, now: datetime) -> tuple[ColumnElement[bool], ...]:
    return (
        UserSession.token_hash == token_hash,
        UserSession.revoked_at.is_(None),
        UserSession.expires_at > now,
    )


async def get_session_owner(session: AsyncSession, token_hash: bytes, now: datetime) -> User | None:
    statement = (
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(*_active_session_filters(token_hash, now), User.status == "active")
    )
    return (await session.scalars(statement)).one_or_none()


async def revoke_session(session: AsyncSession, token_hash: bytes, now: datetime) -> bool:
    statement = (
        update(UserSession)
        .where(*_active_session_filters(token_hash, now))
        .values(revoked_at=now)
        .returning(UserSession.token_hash)
    )
    return (await session.scalar(statement)) is not None
