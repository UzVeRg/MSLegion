from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261123_0013"
down_revision: str | Sequence[str] | None = "20261123_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lc_accounts",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("balance", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_check_in", sa.Date()),
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("balance >= 0", name="ck_lc_accounts_nonnegative_balance"),
        sa.CheckConstraint(
            "(last_check_in IS NULL AND streak = 0) OR (last_check_in IS NOT NULL AND streak > 0)",
            name="ck_lc_accounts_check_in_state",
        ),
    )
    op.create_table(
        "lc_entries",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("lc_accounts.user_id"), primary_key=True),
        sa.Column("source", sa.String(48), primary_key=True),
        sa.Column("operation_key", sa.String(128), primary_key=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount <> 0", name="ck_lc_entries_nonzero_amount"),
    )


def downgrade() -> None:
    op.drop_table("lc_entries")
    op.drop_table("lc_accounts")
