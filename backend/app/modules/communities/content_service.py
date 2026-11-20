from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.modules.auth.service import get_own_profile
from app.modules.communities import content_repository as repository
from app.modules.communities.exceptions import (
    CommunityNotFoundError,
    CommunityPostImageNotFoundError,
    CommunityPostImageTooLargeError,
    CommunityPostImageTypeError,
    CommunityPostNotFoundError,
)
from app.modules.communities.models import MAX_POST_IMAGE_BYTES, CommunityPost
from app.modules.communities.schemas import CommunityPostCreate, CommunityPostRead
from app.modules.communities.service import require_owner
from app.modules.domain_events.repository import record_event


async def create_post(
    session: AsyncSession, token_hash: bytes, community_id: UUID, payload: CommunityPostCreate
) -> CommunityPostRead:
    async with session.begin():
        actor = await get_own_profile(session, token_hash)
        await require_owner(session, actor.id, community_id)
        post = CommunityPost(community_id=community_id, title=payload.title, body=payload.body)
        session.add(post)
        await session.flush()
        record_event(
            session,
            "community.post.published",
            community_id=community_id,
            subject_id=post.id,
            actor_id=actor.id,
        )
        return CommunityPostRead(
            id=post.id,
            title=post.title,
            body=post.body,
            created_at=post.created_at,
            has_image=False,
        )


async def list_posts(
    session: AsyncSession, token_hash: bytes, community_id: UUID, offset: int, limit: int
) -> list[CommunityPostRead]:
    actor = await get_own_profile(session, token_hash)
    posts = await repository.list_visible_posts(session, actor.id, community_id, offset, limit)
    if posts is None:
        raise CommunityNotFoundError
    return posts


async def delete_post(
    session: AsyncSession, token_hash: bytes, community_id: UUID, post_id: UUID
) -> None:
    async with session.begin():
        actor = await get_own_profile(session, token_hash)
        await require_owner(session, actor.id, community_id)
        if not await repository.delete_post(session, community_id, post_id):
            raise CommunityPostNotFoundError
        record_event(
            session,
            "community.post.removed",
            community_id=community_id,
            subject_id=post_id,
            actor_id=actor.id,
        )


def image_type(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n") and content[12:16] == b"IHDR":
        return "image/png"
    if content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9"):
        return "image/jpeg"
    if (
        content.startswith(b"RIFF")
        and content[8:12] == b"WEBP"
        and content[12:16] in (b"VP8 ", b"VP8L", b"VP8X")
        and int.from_bytes(content[4:8], "little") + 8 == len(content)
    ):
        return "image/webp"
    raise CommunityPostImageTypeError


async def read_limited(
    stream: AsyncIterator[bytes], limit: int, limit_error: type[AppError]
) -> bytes:
    data = bytearray()
    async for chunk in stream:
        if len(data) + len(chunk) > limit:
            raise limit_error
        data.extend(chunk)
    return bytes(data)


async def upload_image(
    session: AsyncSession,
    token_hash: bytes,
    community_id: UUID,
    post_id: UUID,
    stream: AsyncIterator[bytes],
) -> None:
    async with session.begin():
        actor = await get_own_profile(session, token_hash)
        await require_owner(session, actor.id, community_id)
        if not await repository.post_exists(session, community_id, post_id):
            raise CommunityPostNotFoundError

    # Загрузка ограничена по размеру и проходит без открытой транзакции.
    content = await read_limited(stream, MAX_POST_IMAGE_BYTES, CommunityPostImageTooLargeError)
    media_type = image_type(content)

    async with session.begin():
        actor = await get_own_profile(session, token_hash)
        await require_owner(session, actor.id, community_id)
        if not await repository.save_image(session, community_id, post_id, media_type, content):
            raise CommunityPostNotFoundError


async def get_image(
    session: AsyncSession, token_hash: bytes, community_id: UUID, post_id: UUID
) -> tuple[str, bytes]:
    actor = await get_own_profile(session, token_hash)
    image = await repository.get_visible_image(session, actor.id, community_id, post_id)
    if image is None:
        raise CommunityPostImageNotFoundError
    return image
