from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261123_0012"
down_revision: str | Sequence[str] | None = "20261123_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mafia_rooms",
        sa.Column("code", sa.String(10), primary_key=True),
        sa.Column(
            "created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_mafia_rooms_creator", "mafia_rooms", ["created_by", "created_at"])
    op.create_index("ix_mafia_rooms_state", "mafia_rooms", ["state"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_table("mafia_rooms")
