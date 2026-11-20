from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, JsonValue

from app.core.exceptions import error_responses
from app.core.security import require_admin_key
from app.core.validation import MAX_BIGINT
from app.modules.auth.router import SessionDependency
from app.modules.domain_events.models import DomainEvent
from app.modules.domain_events.repository import list_events


class DomainEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    community_id: UUID
    subject_id: UUID
    actor_id: UUID | None
    payload: dict[str, JsonValue]
    occurred_at: datetime


router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(require_admin_key)],
    responses=error_responses(401, 422),
)


@router.get(
    "/admin/domain-events",
    response_model=list[DomainEventRead],
    summary="История внутренних событий",
)
async def list_domain_events(
    session: SessionDependency,
    community_id: UUID | None = None,
    offset: Annotated[int, Query(ge=0, le=MAX_BIGINT)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[DomainEvent]:
    return await list_events(session, community_id, offset, limit)
