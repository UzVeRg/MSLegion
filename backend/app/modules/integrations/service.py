from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.integrations import repository
from app.modules.integrations.exceptions import EventIdConflictError
from app.modules.integrations.models import IntegrationEvent
from app.modules.integrations.schemas import CallbackEventCreate


async def receive_event(
    session: AsyncSession,
    payload: CallbackEventCreate,
) -> tuple[IntegrationEvent, bool]:
    async with session.begin():
        event = await repository.insert_event(session, payload)
        if event is not None:
            return event, False
        existing = await repository.get_matching_event(session, payload)
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
