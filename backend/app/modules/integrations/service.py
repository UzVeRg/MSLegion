from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.integrations import repository
from app.modules.integrations.exceptions import CallbackSourceForbiddenError, EventIdConflictError
from app.modules.integrations.models import IntegrationEvent
from app.modules.integrations.schemas import (
    SERVER_STATUS_EVENT_TYPE,
    SERVER_STATUS_SOURCE,
    CallbackEventCreate,
    ServerStatusEventCreate,
)


async def receive_event(
    session: AsyncSession,
    payload: CallbackEventCreate,
) -> tuple[IntegrationEvent, bool]:
    if payload.source == SERVER_STATUS_SOURCE:
        raise CallbackSourceForbiddenError
    return await _save_event(session, payload)


async def receive_server_status(
    session: AsyncSession, payload: ServerStatusEventCreate
) -> tuple[IntegrationEvent, bool]:
    event = CallbackEventCreate(
        source=SERVER_STATUS_SOURCE,
        event_id=payload.event_id,
        event_type=SERVER_STATUS_EVENT_TYPE,
        payload=payload.model_dump(mode="json", exclude={"event_id"}),
    )
    return await _save_event(session, event, processing_state="pending")


async def _save_event(
    session: AsyncSession, payload: CallbackEventCreate, *, processing_state: str | None = None
) -> tuple[IntegrationEvent, bool]:
    async with session.begin():
        event = await repository.insert_event(session, payload, processing_state=processing_state)
        if event is not None:
            return event, False
        existing = await repository.get_matching_event(
            session, payload, processable=processing_state is not None
        )
        if existing is None:
            raise EventIdConflictError
        return existing, True


async def list_events(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 50,
    source: str | None = None,
    event_type: str | None = None,
) -> list[IntegrationEvent]:
    return await repository.list_events(
        session,
        offset=offset,
        limit=limit,
        source=source,
        event_type=event_type,
    )
