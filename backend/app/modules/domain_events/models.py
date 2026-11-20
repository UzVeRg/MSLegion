from datetime import datetime
from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class DomainEvent(Base):
    __tablename__ = "domain_events"
    __table_args__ = (
        Index("ix_domain_events_occurred", "occurred_at", "id"),
        Index("ix_domain_events_community_occurred", "community_id", "occurred_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(64))
    community_id: Mapped[UUID]
    subject_id: Mapped[UUID]
    actor_id: Mapped[UUID | None]
    payload: Mapped[dict[str, JsonValue]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
