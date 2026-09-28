from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.integrations.models import IntegrationEvent
from app.modules.integrations.schemas import CallbackEventCreate


async def create_event(
    session: AsyncSession,
    payload: CallbackEventCreate,
) -> IntegrationEvent:
    event = IntegrationEvent(
        source=payload.source,
        event_id=payload.event_id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    session.add(event)
    return event


async def get_event_by_external_id(
    session: AsyncSession,
    *,
    source: str,
    event_id: str,
) -> IntegrationEvent | None:
    statement: Select[tuple[IntegrationEvent]] = select(IntegrationEvent).where(
        IntegrationEvent.source == source,
        IntegrationEvent.event_id == event_id,
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def list_events(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 50,
    source: str | None = None,
    event_type: str | None = None,
) -> list[IntegrationEvent]:
    statement: Select[tuple[IntegrationEvent]] = select(IntegrationEvent)

    if source is not None:
        statement = statement.where(IntegrationEvent.source == source)

    if event_type is not None:
        statement = statement.where(IntegrationEvent.event_type == event_type)

    statement = (
        statement.order_by(IntegrationEvent.received_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def count_events(session: AsyncSession) -> int:
    statement = select(func.count()).select_from(IntegrationEvent)
    result = await session.execute(statement)
    return int(result.scalar_one())
