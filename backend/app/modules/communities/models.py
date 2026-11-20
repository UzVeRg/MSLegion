from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)


class CommunityMembership(Base):
    __tablename__ = "community_memberships"

    community_id: Mapped[UUID] = mapped_column(
        ForeignKey("communities.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
