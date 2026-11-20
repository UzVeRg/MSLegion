from sqlalchemy import Select, bindparam, func, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.integrations.models import IntegrationEvent
from app.modules.integrations.schemas import CallbackEventCreate


async def insert_event(
    session: AsyncSession,
    payload: CallbackEventCreate,
) -> IntegrationEvent | None:
    statement = (
        insert(IntegrationEvent)
        .values(**payload.model_dump())
        .on_conflict_do_nothing(constraint="uq_integration_events_source_event_id")
        .returning(IntegrationEvent)
    )
    return (await session.scalars(statement)).one_or_none()


async def get_matching_event(
    session: AsyncSession,
    payload: CallbackEventCreate,
) -> IntegrationEvent | None:
    statement = select(IntegrationEvent).where(
        IntegrationEvent.source == payload.source,
        IntegrationEvent.event_id == payload.event_id,
        IntegrationEvent.event_type == payload.event_type,
        IntegrationEvent.payload == bindparam("expected_payload", payload.payload, type_=JSONB),
    )
    return (await session.scalars(statement)).one_or_none()


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
        statement.order_by(IntegrationEvent.received_at.desc(), IntegrationEvent.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def count_events(session: AsyncSession) -> int:
    statement = select(func.count()).select_from(IntegrationEvent)
    result = await session.execute(statement)
    return int(result.scalar_one())
