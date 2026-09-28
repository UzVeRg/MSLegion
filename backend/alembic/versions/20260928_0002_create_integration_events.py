from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260928_0002"
down_revision: str | Sequence[str] | None = "20260928_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source",
            "event_id",
            name="uq_integration_events_source_event_id",
        ),
    )
    op.create_index(
        "ix_integration_events_source",
        "integration_events",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_integration_events_event_type",
        "integration_events",
        ["event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_integration_events_event_type",
        table_name="integration_events",
    )
    op.drop_index(
        "ix_integration_events_source",
        table_name="integration_events",
    )
    op.drop_table("integration_events")
