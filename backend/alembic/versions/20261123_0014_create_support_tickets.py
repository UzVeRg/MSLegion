from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261123_0014"
down_revision: str | Sequence[str] | None = "20261123_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("answered_by", sa.BigInteger(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("author_id", "message_id", name="uq_support_tickets_message"),
    )
    op.create_index("ix_support_tickets_author", "support_tickets", ["author_id", "id"])
    op.create_index(
        "ix_support_tickets_open", "support_tickets", ["id"],
        postgresql_where=sa.text("closed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("support_tickets")
