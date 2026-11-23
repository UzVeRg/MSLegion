from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        UniqueConstraint("author_id", "message_id", name="uq_support_tickets_message"),
        Index("ix_support_tickets_open", "id", postgresql_where=text("closed_at IS NULL")),
        Index("ix_support_tickets_author", "author_id", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    author_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    answer: Mapped[str | None] = mapped_column(Text)
    answered_by: Mapped[int | None] = mapped_column(BigInteger)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
