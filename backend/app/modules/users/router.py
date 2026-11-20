import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import error_responses
from app.core.security import require_admin_key
from app.core.validation import MAX_BIGINT
from app.modules.users import service as user_service
from app.modules.users.schemas import UserCreate, UserRead, UserTelegramConfirmation

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_admin_key)],
    responses=error_responses(401, 422),
)

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409),
)
async def create_user(
    payload: UserCreate,
    session: SessionDependency,
) -> UserRead:
    return await user_service.create_user(session, payload)


@router.get(
    "",
    response_model=list[UserRead],
)
async def list_users(
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0, le=MAX_BIGINT)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[UserRead]:
    return await user_service.list_users(
        session,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
    responses=error_responses(404),
)
async def get_user(
    user_id: uuid.UUID,
    session: SessionDependency,
) -> UserRead:
    return await user_service.get_user(session, user_id)


@router.put(
    "/{user_id}/telegram/confirmation",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Подтвердить привязку пользователя к Telegram",
    responses=error_responses(404, 409),
)
async def confirm_telegram_binding(
    user_id: uuid.UUID,
    payload: UserTelegramConfirmation,
    session: SessionDependency,
) -> None:
    await user_service.confirm_telegram_binding(session, user_id, payload.telegram_id)
