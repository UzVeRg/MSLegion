from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, LargeBinary, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index(
            "ix_user_sessions_revoked",
            "token_hash",
            postgresql_where=text("revoked_at IS NOT NULL"),
        ),
    )

    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
