from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class TelegramNotification(Base):
    __tablename__ = "telegram_notifications"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued', 'sending', 'sent', 'failed', 'uncertain', 'canceled')",
            name="ck_telegram_notifications_state",
        ),
        Index(
            "ix_telegram_notifications_queued",
            "created_at",
            "event_id",
            postgresql_where=text("state = 'queued'"),
        ),
    )

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("integration_events.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    message: Mapped[str] = mapped_column(String(256))
    state: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
