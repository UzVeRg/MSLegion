from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class MafiaRoom(Base):
    __tablename__ = "mafia_rooms"
    __table_args__ = (
        Index("ix_mafia_rooms_creator", "created_by", "created_at"),
        Index("ix_mafia_rooms_state", "state", postgresql_using="gin"),
    )

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[dict] = mapped_column(JSONB)
