from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_0003"
down_revision: str | Sequence[str] | None = "20260928_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("telegram_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_check_constraint(
        "ck_users_telegram_verified_requires_id",
        "users",
        "NOT telegram_verified OR telegram_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_telegram_verified_requires_id", "users", type_="check")
    op.drop_column("users", "telegram_verified")
