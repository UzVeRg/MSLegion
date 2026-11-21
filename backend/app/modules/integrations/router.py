from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import error_responses
from app.core.request_body import MAX_CALLBACK_BODY_BYTES, LimitedJSONRoute
from app.core.security import require_admin_key, require_callback_key, require_server_status_key
from app.core.validation import MAX_BIGINT, DatabaseText
from app.modules.integrations import processing, repository, service
from app.modules.integrations.schemas import (
    CallbackEventCreate,
    CallbackReceipt,
    IntegrationEventRead,
    ProcessingMetrics,
    ProcessingSummary,
    ServerStatusEventCreate,
)

router = APIRouter(
    tags=["integrations"], route_class=LimitedJSONRoute, responses=error_responses(401, 422)
)

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/callbacks/events",
    response_model=CallbackReceipt,
    responses=error_responses(403, 409, 413),
    openapi_extra={"x-max-body-bytes": MAX_CALLBACK_BODY_BYTES},
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


@router.post(
    "/callbacks/server-status",
    response_model=CallbackReceipt,
    responses=error_responses(409, 413),
    dependencies=[Depends(require_server_status_key)],
    summary="Принять наблюдение статуса сервера",
)
async def receive_server_status(
    payload: ServerStatusEventCreate,
    session: SessionDependency,
) -> CallbackReceipt:
    event, duplicate = await service.receive_server_status(session, payload)
    return CallbackReceipt(duplicate=duplicate, event=IntegrationEventRead.model_validate(event))


@router.post(
    "/admin/callbacks/process",
    response_model=ProcessingSummary,
    dependencies=[Depends(require_admin_key)],
    summary="Обработать ожидающие события",
)
async def process_callback_events(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ProcessingSummary:
    return await processing.process_pending_events(session, limit)


@router.get(
    "/admin/callbacks/processing",
    dependencies=[Depends(require_admin_key)],
    summary="Получить показатели обработки событий",
)
async def get_processing_metrics(session: SessionDependency) -> ProcessingMetrics:
    return await repository.get_processing_metrics(session)


@router.get(
    "/admin/callbacks",
    response_model=list[IntegrationEventRead],
    dependencies=[Depends(require_admin_key)],
)
async def list_callback_events(
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0, le=MAX_BIGINT)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    source: Annotated[DatabaseText | None, Query(min_length=1, max_length=64)] = None,
    event_type: Annotated[DatabaseText | None, Query(min_length=1, max_length=128)] = None,
) -> list[IntegrationEventRead]:
    return await service.list_events(
        session,
        offset=offset,
        limit=limit,
        source=source,
        event_type=event_type,
    )
