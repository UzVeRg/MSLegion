import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.users import service as user_service
from app.modules.users.schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
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
    offset: Annotated[int, Query(ge=0)] = 0,
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
)
async def get_user(
    user_id: uuid.UUID,
    session: SessionDependency,
) -> UserRead:
    return await user_service.get_user(session, user_id)
