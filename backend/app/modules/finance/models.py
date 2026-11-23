from datetime import date, datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class LCAccount(Base):
    __tablename__ = "lc_accounts"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_lc_accounts_nonnegative_balance"),
        CheckConstraint(
            "(last_check_in IS NULL AND streak = 0) OR (last_check_in IS NOT NULL AND streak > 0)",
            name="ck_lc_accounts_check_in_state",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("users.id"), primary_key=True)
    balance: Mapped[int] = mapped_column(BigInteger, server_default="0")
    last_check_in: Mapped[date | None] = mapped_column(Date)
    streak: Mapped[int] = mapped_column(server_default="0")


class LCEntry(Base):
    __tablename__ = "lc_entries"
    __table_args__ = (CheckConstraint("amount <> 0", name="ck_lc_entries_nonzero_amount"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("lc_accounts.user_id"), primary_key=True,
    )
    source: Mapped[str] = mapped_column(String(48), primary_key=True)
    operation_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
