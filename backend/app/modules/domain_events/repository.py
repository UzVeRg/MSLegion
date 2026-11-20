from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.domain_events.models import DomainEvent


def record_event(
    session: AsyncSession,
    event_type: str,
    *,
    community_id: UUID,
    subject_id: UUID,
    actor_id: UUID | None = None,
    payload: dict[str, JsonValue] | None = None,
) -> None:
    session.add(
        DomainEvent(
            event_type=event_type,
            community_id=community_id,
            subject_id=subject_id,
            actor_id=actor_id,
            payload=payload if payload is not None else {},
        )
    )


async def list_events(
    session: AsyncSession, community_id: UUID | None, offset: int, limit: int
) -> list[DomainEvent]:
    statement = select(DomainEvent)
    if community_id is not None:
        statement = statement.where(DomainEvent.community_id == community_id)
    statement = statement.order_by(DomainEvent.occurred_at.desc(), DomainEvent.id.desc())
    return list(await session.scalars(statement.offset(offset).limit(limit)))
