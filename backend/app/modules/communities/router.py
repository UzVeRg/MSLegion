from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.exceptions import error_responses
from app.core.validation import MAX_BIGINT
from app.modules.auth.router import SessionDependency, TokenHash
from app.modules.communities import service
from app.modules.communities.models import Community, CommunityMembership, CommunityServer
from app.modules.communities.schemas import (
    CommunityCreate,
    CommunityRead,
    CommunityServerCreate,
    CommunityServerRead,
    MembershipRead,
)

router = APIRouter(prefix="/communities", tags=["communities"], responses=error_responses(401, 422))
Offset = Annotated[int, Query(ge=0, le=MAX_BIGINT)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post(
    "",
    response_model=CommunityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать сообщество",
)
async def create_community(
    payload: CommunityCreate, token_hash: TokenHash, session: SessionDependency
) -> Community:
    return await service.create_community(session, token_hash, payload.name)


@router.get("", response_model=list[CommunityRead], summary="Список моих сообществ")
async def list_communities(
    token_hash: TokenHash, session: SessionDependency, offset: Offset = 0, limit: Limit = 50
) -> list[Community]:
    return await service.list_communities(session, token_hash, offset, limit)


@router.get(
    "/{community_id}",
    response_model=CommunityRead,
    responses=error_responses(404),
    summary="Получить сообщество",
)
async def get_community(
    community_id: UUID, token_hash: TokenHash, session: SessionDependency
) -> Community:
    return await service.get_community(session, token_hash, community_id)


@router.get(
    "/{community_id}/members",
    response_model=list[MembershipRead],
    responses=error_responses(403, 404),
    summary="Список участников сообщества",
)
async def list_members(
    community_id: UUID,
    token_hash: TokenHash,
    session: SessionDependency,
    offset: Offset = 0,
    limit: Limit = 50,
) -> list[CommunityMembership]:
    return await service.list_members(session, token_hash, community_id, offset, limit)


@router.put(
    "/{community_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(403, 404),
    summary="Добавить участника сообщества",
)
async def add_member(
    community_id: UUID, user_id: UUID, token_hash: TokenHash, session: SessionDependency
) -> None:
    await service.add_member(session, token_hash, community_id, user_id)


@router.delete(
    "/{community_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(403, 404, 409),
    summary="Исключить участника сообщества",
)
async def remove_member(
    community_id: UUID, user_id: UUID, token_hash: TokenHash, session: SessionDependency
) -> None:
    await service.remove_member(session, token_hash, community_id, user_id)


@router.get(
    "/{community_id}/servers",
    response_model=list[CommunityServerRead],
    responses=error_responses(404),
    summary="Список серверов сообщества",
)
async def list_servers(
    community_id: UUID,
    token_hash: TokenHash,
    session: SessionDependency,
    offset: Offset = 0,
    limit: Limit = 50,
) -> list[CommunityServer]:
    return await service.list_servers(session, token_hash, community_id, offset, limit)


@router.post(
    "/{community_id}/servers",
    response_model=CommunityServerRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(403, 404, 409),
    summary="Зарегистрировать сервер сообщества",
)
async def register_server(
    community_id: UUID,
    payload: CommunityServerCreate,
    token_hash: TokenHash,
    session: SessionDependency,
) -> CommunityServer:
    return await service.register_server(session, token_hash, community_id, payload)


@router.delete(
    "/{community_id}/servers/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(403, 404),
    summary="Удалить сервер сообщества",
)
async def remove_server(
    community_id: UUID, server_id: UUID, token_hash: TokenHash, session: SessionDependency
) -> None:
    await service.remove_server(session, token_hash, community_id, server_id)
