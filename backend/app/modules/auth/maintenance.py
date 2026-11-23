from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import UserSession


async def purge_inactive_sessions(session: AsyncSession) -> int:
    async with session.begin():
        batch = (
            select(UserSession.token_hash)
            .where(or_(UserSession.expires_at <= func.now(), UserSession.revoked_at.is_not(None)))
            .limit(500)
            .with_for_update(skip_locked=True)
            .cte("batch")
        )
        statement = delete(UserSession.__table__).where(
            UserSession.token_hash == batch.c.token_hash
        )
        result = await session.execute(statement)
        return result.rowcount
