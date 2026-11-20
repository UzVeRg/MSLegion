import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class IntegrationEvent(Base):
    __tablename__ = "integration_events"
    __table_args__ = (
        Index(
            "uq_integration_events_general_source_event_id",
            "source",
            "event_id",
            unique=True,
            postgresql_where=text("processing_state IS NULL"),
        ),
        Index(
            "uq_integration_events_scoped_source_event_id",
            "source",
            "event_id",
            unique=True,
            postgresql_where=text("processing_state IS NOT NULL"),
        ),
        CheckConstraint(
            "processing_state IN ('pending', 'applied', 'ignored', 'rejected')",
            name="ck_integration_events_processing_state",
        ),
        Index(
            "ix_integration_events_pending",
            "received_at",
            "id",
            postgresql_where=text("processing_state = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    payload: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    processing_state: Mapped[str | None] = mapped_column(String(16))
