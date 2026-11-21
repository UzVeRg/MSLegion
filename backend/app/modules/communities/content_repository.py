from uuid import UUID

from sqlalchemy import delete, func, select, text, true, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.communities.models import Community, CommunityPost
from app.modules.communities.repository import visible_to
from app.modules.communities.schemas import CommunityPostRead
from app.modules.users.models import User


async def list_visible_posts(
    session: AsyncSession, actor_id: UUID, community_id: UUID, offset: int, limit: int
) -> list[CommunityPostRead] | None:
    page = (
        select(
            CommunityPost.id,
            CommunityPost.title,
            CommunityPost.body,
            CommunityPost.created_at,
            CommunityPost.image_type.is_not(None).label("has_image"),
        )
        .where(CommunityPost.community_id == community_id)
        .order_by(CommunityPost.created_at.desc(), CommunityPost.id.desc())
        .offset(offset)
        .limit(limit)
        .subquery()
    )
    query = (
        select(*page.c)
        .select_from(Community)
        .outerjoin(page, true())
        .where(Community.id == community_id, visible_to(actor_id))
        .order_by(page.c.created_at.desc(), page.c.id.desc())
    )
    rows = (await session.execute(query)).mappings().all()
    if not rows:
        return None
    return [CommunityPostRead.model_validate(row) for row in rows if row["id"] is not None]


async def get_post_image_size(
    session: AsyncSession, community_id: UUID, post_id: UUID
) -> int | None:
    query = select(func.coalesce(func.octet_length(CommunityPost.image), 0)).where(
        CommunityPost.community_id == community_id, CommunityPost.id == post_id
    )
    return await session.scalar(query)


async def lock_owner_image_quota(session: AsyncSession, owner_id: UUID) -> None:
    # После ожидания блокировки подсчёт должен увидеть последнюю завершённую загрузку.
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
    await session.execute(select(User.id).where(User.id == owner_id).with_for_update())


async def get_owner_image_bytes(session: AsyncSession, owner_id: UUID) -> int:
    query = (
        select(func.coalesce(func.sum(func.octet_length(CommunityPost.image)), 0))
        .select_from(CommunityPost)
        .join(Community, Community.id == CommunityPost.community_id)
        .where(Community.owner_id == owner_id, CommunityPost.image.is_not(None))
    )
    return (await session.execute(query)).scalar_one()


async def delete_post(session: AsyncSession, community_id: UUID, post_id: UUID) -> bool:
    statement = (
        delete(CommunityPost)
        .where(CommunityPost.community_id == community_id, CommunityPost.id == post_id)
        .returning(CommunityPost.id)
    )
    return await session.scalar(statement) is not None


async def save_image(
    session: AsyncSession, community_id: UUID, post_id: UUID, media_type: str, content: bytes
) -> bool:
    statement = (
        update(CommunityPost)
        .where(CommunityPost.community_id == community_id, CommunityPost.id == post_id)
        .values(image_type=media_type, image=content)
        .returning(CommunityPost.id)
    )
    return await session.scalar(statement) is not None


async def get_visible_image(
    session: AsyncSession, actor_id: UUID, community_id: UUID, post_id: UUID
) -> tuple[str, bytes] | None:
    query = (
        select(CommunityPost.image_type, CommunityPost.image)
        .join(Community, Community.id == CommunityPost.community_id)
        .where(
            Community.id == community_id,
            CommunityPost.id == post_id,
            visible_to(actor_id),
            CommunityPost.image_type.is_not(None),
        )
    )
    row = (await session.execute(query)).one_or_none()
    if row is None:
        return None
    media_type, content = row
    return media_type, content
