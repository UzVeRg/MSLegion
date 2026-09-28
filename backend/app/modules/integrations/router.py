from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import require_admin_key, require_callback_key
from app.modules.integrations import service
from app.modules.integrations.schemas import (
    CallbackEventCreate,
    CallbackReceipt,
    IntegrationEventRead,
)

router = APIRouter(tags=["integrations"])

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/callbacks/events",
    response_model=CallbackReceipt,
    dependencies=[Depends(require_callback_key)],
)
async def receive_event(
    payload: CallbackEventCreate,
    session: SessionDependency,
) -> CallbackReceipt:
    event, duplicate = await service.receive_event(session, payload)
    return CallbackReceipt(
        duplicate=duplicate,
        event=IntegrationEventRead.model_validate(event),
    )


@router.get(
    "/admin/callbacks",
    response_model=list[IntegrationEventRead],
    dependencies=[Depends(require_admin_key)],
)
async def list_callback_events(
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    source: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    event_type: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
) -> list[IntegrationEventRead]:
    return await service.list_events(
        session,
        offset=offset,
        limit=limit,
        source=source,
        event_type=event_type,
    )
