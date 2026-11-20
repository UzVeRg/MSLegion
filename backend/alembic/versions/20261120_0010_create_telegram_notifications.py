from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_0010"
down_revision: str | Sequence[str] | None = "20261120_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_notifications_since", sa.DateTime(timezone=True)))
    op.create_table(
        "telegram_notifications",
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("integration_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("message", sa.String(256), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("attempted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "state IN ('queued', 'sending', 'sent', 'failed', 'uncertain', 'canceled')",
            name="ck_telegram_notifications_state",
        ),
    )
    op.create_index(
        "ix_telegram_notifications_queued",
        "telegram_notifications",
        ["created_at", "event_id"],
        postgresql_where=sa.text("state = 'queued'"),
    )


def downgrade() -> None:
    op.drop_table("telegram_notifications")
    op.drop_column("users", "telegram_notifications_since")
