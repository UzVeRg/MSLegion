from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
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


class CommunityServer(Base):
    __tablename__ = "community_servers"
    __table_args__ = (
        UniqueConstraint("community_id", "host", "port", name="uq_community_servers_endpoint"),
        CheckConstraint("port BETWEEN 1 AND 65535", name="ck_community_servers_port"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    community_id: Mapped[UUID] = mapped_column(ForeignKey("communities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    host: Mapped[str] = mapped_column(String(253))
    port: Mapped[int]
