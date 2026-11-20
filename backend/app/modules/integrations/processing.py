from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.communities.models import CommunityServer
from app.modules.domain_events.repository import record_event
from app.modules.integrations import repository
from app.modules.integrations.models import IntegrationEvent
from app.modules.integrations.schemas import (
    SERVER_STATUS_EVENT_TYPE,
    SERVER_STATUS_SOURCE,
    ProcessingOutcome,
    ProcessingSummary,
    ServerStatusPayload,
)


async def apply_server_status(session: AsyncSession, event: IntegrationEvent) -> ProcessingOutcome:
    if event.source != SERVER_STATUS_SOURCE or event.event_type != SERVER_STATUS_EVENT_TYPE:
        return "rejected"
    try:
        payload = ServerStatusPayload.model_validate(event.payload)
    except ValidationError:
        return "rejected"
    server = await session.get(CommunityServer, payload.server_id, with_for_update=True)
    if server is None:
        return "rejected"

    if server.status_observed_at is not None and (
        payload.observed_at < server.status_observed_at
        or (
            payload.observed_at == server.status_observed_at
            and server.status_event_id is not None
            and event.id <= server.status_event_id
        )
    ):
        return "ignored"
    server.online = payload.online
    server.status_observed_at = payload.observed_at
    server.status_event_id = event.id
    record_event(
        session,
        "community.server.status_observed",
        community_id=server.community_id,
        subject_id=server.id,
        payload={"online": payload.online, "observed_at": payload.observed_at.isoformat()},
    )
    return "applied"


async def process_pending_events(session: AsyncSession, limit: int) -> ProcessingSummary:
    counts = {"applied": 0, "ignored": 0, "rejected": 0}
    for _ in range(limit):
        # Отдельная транзакция на событие фиксирует эффект вместе с его итогом.
        async with session.begin():
            event = await repository.claim_pending_event(session)
            if event is None:
                break
            outcome = await apply_server_status(session, event)
            event.processing_state = outcome
        counts[outcome] += 1
    return ProcessingSummary(**counts)
