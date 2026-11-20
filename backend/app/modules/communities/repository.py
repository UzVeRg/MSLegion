from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.communities.models import Community, CommunityMembership, CommunityServer
from app.modules.communities.schemas import CommunityServerCreate, CommunityStatistics


def visible_to(user_id: UUID) -> ColumnElement[bool]:
    membership = (
        select(CommunityMembership.community_id)
        .where(CommunityMembership.community_id == Community.id)
        .where(CommunityMembership.user_id == user_id)
        .exists()
    )
    return (Community.owner_id == user_id) | membership


async def list_visible_communities(
    session: AsyncSession, user_id: UUID, offset: int, limit: int
) -> list[Community]:
    query = (
        select(Community)
        .where(visible_to(user_id))
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


async def insert_membership(session: AsyncSession, community_id: UUID, user_id: UUID) -> bool:
    statement = (
        insert(CommunityMembership)
        .values(community_id=community_id, user_id=user_id)
        .on_conflict_do_nothing(index_elements=["community_id", "user_id"])
        .returning(CommunityMembership.user_id)
    )
    return (await session.scalar(statement)) is not None


async def list_visible_servers(
    session: AsyncSession, user_id: UUID, community_id: UUID, offset: int, limit: int
) -> list[CommunityServer] | None:
    page = (
        select(CommunityServer)
        .where(CommunityServer.community_id == community_id)
        .order_by(CommunityServer.id)
        .offset(offset)
        .limit(limit)
        .subquery()
    )
    server = aliased(CommunityServer, page)
    # Внешнее соединение отличает пустую страницу от недоступного сообщества.
    query = (
        select(Community.id, server)
        .outerjoin(server, server.community_id == Community.id)
        .where(Community.id == community_id, visible_to(user_id))
        .order_by(server.id)
    )
    rows = (await session.execute(query)).all()
    return [record for _, record in rows if record is not None] if rows else None


async def insert_server(
    session: AsyncSession, community_id: UUID, payload: CommunityServerCreate
) -> CommunityServer | None:
    statement = (
        insert(CommunityServer)
        .values(community_id=community_id, name=payload.name, host=payload.host, port=payload.port)
        .on_conflict_do_nothing(constraint="uq_community_servers_endpoint")
        .returning(CommunityServer)
    )
    return await session.scalar(statement)


async def delete_server(session: AsyncSession, community_id: UUID, server_id: UUID) -> bool:
    statement = (
        delete(CommunityServer)
        .where(CommunityServer.community_id == community_id, CommunityServer.id == server_id)
        .returning(CommunityServer.id)
    )
    return (await session.scalar(statement)) is not None


async def get_visible_statistics(
    session: AsyncSession, user_id: UUID, community_id: UUID
) -> CommunityStatistics | None:
    # Владелец учитывается в составе отдельно от строк членства.
    members = (
        select(func.count())
        .select_from(CommunityMembership)
        .where(CommunityMembership.community_id == community_id)
        .scalar_subquery()
        + 1
    )
    servers = (
        select(
            func.count().label("servers"),
            func.count().filter(CommunityServer.online.is_(True)).label("online"),
            func.count().filter(CommunityServer.online.is_(False)).label("offline"),
            func.count().filter(CommunityServer.online.is_(None)).label("unobserved"),
        )
        .where(CommunityServer.community_id == community_id)
        .subquery()
    )
    query = (
        select(members.label("members"), *servers.c)
        .select_from(Community)
        .join(servers, true())
        .where(Community.id == community_id, visible_to(user_id))
    )
    row = (await session.execute(query)).mappings().one_or_none()
    return CommunityStatistics.model_validate(row) if row is not None else None
