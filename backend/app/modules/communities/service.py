from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.service import get_own_profile
from app.modules.communities import repository
from app.modules.communities.exceptions import (
    CommunityNotFoundError,
    CommunityOwnerRemovalError,
    CommunityOwnerRequiredError,
)
from app.modules.communities.models import Community, CommunityMembership
from app.modules.users.service import get_user


async def _require_visible(
    session: AsyncSession, actor_id: UUID, community_id: UUID, *, for_update: bool = False
) -> Community:
    community = await session.get(Community, community_id, with_for_update=for_update)
    if community is None:
        raise CommunityNotFoundError
    if community.owner_id != actor_id and not await session.get(
        CommunityMembership, (community_id, actor_id)
    ):
        raise CommunityNotFoundError
    return community


async def _require_owner(
    session: AsyncSession, actor_id: UUID, community_id: UUID, *, for_update: bool = False
) -> Community:
    community = await _require_visible(session, actor_id, community_id, for_update=for_update)
    if community.owner_id != actor_id:
        raise CommunityOwnerRequiredError
    return community


async def create_community(session: AsyncSession, token_hash: bytes, name: str) -> Community:
    async with session.begin():
        actor = await get_own_profile(session, token_hash)
        community = Community(name=name, owner_id=actor.id)
        session.add(community)
    return community


async def list_communities(
    session: AsyncSession, token_hash: bytes, offset: int, limit: int
) -> list[Community]:
    actor = await get_own_profile(session, token_hash)
    return await repository.list_visible_communities(session, actor.id, offset, limit)


async def get_community(session: AsyncSession, token_hash: bytes, community_id: UUID) -> Community:
    actor = await get_own_profile(session, token_hash)
    return await _require_visible(session, actor.id, community_id)


async def list_members(
    session: AsyncSession, token_hash: bytes, community_id: UUID, offset: int, limit: int
) -> list[CommunityMembership]:
    actor = await get_own_profile(session, token_hash)
    await _require_owner(session, actor.id, community_id)
    return await repository.list_members(session, community_id, offset, limit)


async def add_member(
    session: AsyncSession, token_hash: bytes, community_id: UUID, member_id: UUID
) -> None:
    async with session.begin():
        actor = await get_own_profile(session, token_hash)
        community = await _require_owner(session, actor.id, community_id, for_update=True)
        if member_id == community.owner_id:
            return
        await get_user(session, member_id)
        await repository.insert_membership(session, community_id, member_id)


async def remove_member(
    session: AsyncSession, token_hash: bytes, community_id: UUID, member_id: UUID
) -> None:
    async with session.begin():
        actor = await get_own_profile(session, token_hash)
        community = await _require_owner(session, actor.id, community_id, for_update=True)
        if member_id == community.owner_id:
            raise CommunityOwnerRemovalError
        membership = await session.get(CommunityMembership, (community_id, member_id))
        if membership is not None:
            await session.delete(membership)
