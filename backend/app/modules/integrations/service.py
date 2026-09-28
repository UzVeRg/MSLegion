from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.integrations import repository
from app.modules.integrations.models import IntegrationEvent
from app.modules.integrations.schemas import CallbackEventCreate


async def receive_event(
    session: AsyncSession,
    payload: CallbackEventCreate,
) -> tuple[IntegrationEvent, bool]:
    existing = await repository.get_event_by_external_id(
        session,
        source=payload.source,
        event_id=payload.event_id,
    )
    if existing is not None:
        return existing, True

    event = await repository.create_event(session, payload)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await repository.get_event_by_external_id(
            session,
            source=payload.source,
            event_id=payload.event_id,
        )
        if existing is None:
            raise
        return existing, True

    await session.refresh(event)
    return event, False


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
