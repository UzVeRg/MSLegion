from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.communities.models import Community, CommunityMembership


async def list_visible_communities(
    session: AsyncSession, user_id: UUID, offset: int, limit: int
) -> list[Community]:
    membership = (
        select(CommunityMembership.community_id)
        .where(CommunityMembership.community_id == Community.id)
        .where(CommunityMembership.user_id == user_id)
        .exists()
    )
    query = (
        select(Community)
        .where((Community.owner_id == user_id) | membership)
        .order_by(Community.id)
        .offset(offset)
        .limit(limit)
    )
    return list(await session.scalars(query))


async def list_members(
    session: AsyncSession, community_id: UUID, offset: int, limit: int
) -> list[CommunityMembership]:
    query = (
        select(CommunityMembership)
        .where(CommunityMembership.community_id == community_id)
        .order_by(CommunityMembership.user_id)
        .offset(offset)
        .limit(limit)
    )
    return list(await session.scalars(query))


async def insert_membership(session: AsyncSession, community_id: UUID, user_id: UUID) -> None:
    statement = (
        insert(CommunityMembership)
        .values(community_id=community_id, user_id=user_id)
        .on_conflict_do_nothing(index_elements=["community_id", "user_id"])
    )
    await session.execute(statement)
