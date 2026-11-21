from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import error_responses
from app.modules.auth.router import SessionDependency, TokenHash
from app.modules.communities import content_service as service
from app.modules.communities.exceptions import CommunityPostTooLargeError
from app.modules.communities.router import Limit, Offset
from app.modules.communities.schemas import CommunityPostCreate, CommunityPostRead

MAX_POST_REQUEST_BYTES = 131_072

router = APIRouter(
    prefix="/communities/{community_id}/posts",
    tags=["communities"],
    responses=error_responses(401, 404, 422),
)


@router.get("", summary="Публикации сообщества")
async def list_posts(
    community_id: UUID,
    token_hash: TokenHash,
    session: SessionDependency,
    response: Response,
    offset: Offset = 0,
    limit: Limit = 50,
) -> list[CommunityPostRead]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_posts(session, token_hash, community_id, offset, limit)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(403, 413),
    summary="Создать публикацию",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": CommunityPostCreate.model_json_schema()}},
        },
    },
)
async def create_post(
    community_id: UUID,
    request: Request,
    token_hash: TokenHash,
    session: SessionDependency,
) -> CommunityPostRead:
    content = await service.read_limited(
        request.stream(), MAX_POST_REQUEST_BYTES, CommunityPostTooLargeError
    )
    try:
        payload = CommunityPostCreate.model_validate_json(content)
    except ValidationError as exc:
        errors = [
            {"type": error["type"], "msg": error["msg"], "loc": ("body", *error["loc"])}
            for error in exc.errors(include_input=False)
        ]
        raise RequestValidationError(errors) from None
    return await service.create_post(session, token_hash, community_id, payload)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(403),
    summary="Удалить публикацию и её изображение",
)
async def delete_post(
    community_id: UUID,
    post_id: UUID,
    token_hash: TokenHash,
    session: SessionDependency,
) -> None:
    await service.delete_post(session, token_hash, community_id, post_id)


@router.put(
    "/{post_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(403, 409, 413, 415),
    summary="Загрузить или заменить изображение публикации",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                    }
                }
            },
        },
    },
)
async def upload_image(
    community_id: UUID,
    post_id: UUID,
    request: Request,
    token_hash: TokenHash,
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    await service.upload_image(
        session,
        token_hash,
        community_id,
        post_id,
        request.stream(),
        owner_quota_bytes=settings.owner_image_quota_bytes,
    )


@router.get(
    "/{post_id}/image",
    response_class=Response,
    summary="Скачать изображение публикации",
    responses={
        200: {
            "content": {
                media_type: {"schema": {"type": "string", "format": "binary"}}
                for media_type in ("image/png", "image/jpeg", "image/webp")
            }
        },
    },
)
async def get_image(
    community_id: UUID,
    post_id: UUID,
    token_hash: TokenHash,
    session: SessionDependency,
) -> Response:
    media_type, content = await service.get_image(session, token_hash, community_id, post_id)
    extension = media_type.split("/", maxsplit=1)[1]
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'attachment; filename="image.{extension}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
