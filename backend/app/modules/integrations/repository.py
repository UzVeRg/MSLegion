from sqlalchemy import Select, bindparam, func, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.integrations.models import IntegrationEvent
from app.modules.integrations.schemas import CallbackEventCreate, ProcessingMetrics


def _processing_scope(processable: bool):
    if processable:
        return IntegrationEvent.processing_state.is_not(None)
    return IntegrationEvent.processing_state.is_(None)


async def insert_event(
    session: AsyncSession,
    payload: CallbackEventCreate,
    *,
    processing_state: str | None = None,
) -> IntegrationEvent | None:
    statement = (
        insert(IntegrationEvent)
        .values(**payload.model_dump(), processing_state=processing_state)
        .on_conflict_do_nothing(
            index_elements=[IntegrationEvent.source, IntegrationEvent.event_id],
            index_where=_processing_scope(processing_state is not None),
        )
        .returning(IntegrationEvent)
    )
    return (await session.scalars(statement)).one_or_none()


async def claim_pending_event(session: AsyncSession) -> IntegrationEvent | None:
    statement = (
        select(IntegrationEvent)
        .where(IntegrationEvent.processing_state == "pending")
        .order_by(IntegrationEvent.received_at, IntegrationEvent.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    return await session.scalar(statement)


async def get_matching_event(
    session: AsyncSession,
    payload: CallbackEventCreate,
    *,
    processable: bool = False,
) -> IntegrationEvent | None:
    statement = select(IntegrationEvent).where(
        IntegrationEvent.source == payload.source,
        IntegrationEvent.event_id == payload.event_id,
        IntegrationEvent.event_type == payload.event_type,
        IntegrationEvent.payload == bindparam("expected_payload", payload.payload, type_=JSONB),
        _processing_scope(processable),
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


async def get_processing_metrics(session: AsyncSession) -> ProcessingMetrics:
    state = IntegrationEvent.processing_state
    statement = select(
        func.count().filter(state == "pending").label("pending"),
        func.count().filter(state == "applied").label("applied"),
        func.count().filter(state == "ignored").label("ignored"),
        func.count().filter(state == "rejected").label("rejected"),
        func.min(IntegrationEvent.received_at)
        .filter(state == "pending")
        .label("oldest_pending_at"),
    ).where(state.is_not(None))
    row = (await session.execute(statement)).mappings().one()
    return ProcessingMetrics.model_validate(row)
