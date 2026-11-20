from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_0007"
down_revision: str | Sequence[str] | None = "20261120_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("integration_events", sa.Column("processing_state", sa.String(16)))
    op.drop_constraint(
        "uq_integration_events_source_event_id", "integration_events", type_="unique"
    )
    for index, predicate in (
        ("uq_integration_events_general_source_event_id", "processing_state IS NULL"),
        ("uq_integration_events_scoped_source_event_id", "processing_state IS NOT NULL"),
    ):
        op.create_index(
            index,
            "integration_events",
            ["source", "event_id"],
            unique=True,
            postgresql_where=sa.text(predicate),
        )
    op.create_check_constraint(
        "ck_integration_events_processing_state",
        "integration_events",
        "processing_state IN ('pending', 'applied', 'ignored', 'rejected')",
    )
    op.create_index(
        "ix_integration_events_pending",
        "integration_events",
        ["received_at", "id"],
        postgresql_where=sa.text("processing_state = 'pending'"),
    )
    op.add_column("community_servers", sa.Column("online", sa.Boolean()))
    op.add_column("community_servers", sa.Column("status_observed_at", sa.DateTime(timezone=True)))
    op.add_column("community_servers", sa.Column("status_event_id", sa.Uuid()))


def downgrade() -> None:
    # При совпадении старой и новой записей PostgreSQL остановит откат до удаления полей.
    op.create_unique_constraint(
        "uq_integration_events_source_event_id", "integration_events", ["source", "event_id"]
    )
    op.drop_index("uq_integration_events_scoped_source_event_id", table_name="integration_events")
    op.drop_index("uq_integration_events_general_source_event_id", table_name="integration_events")
    op.drop_column("community_servers", "status_event_id")
    op.drop_column("community_servers", "status_observed_at")
    op.drop_column("community_servers", "online")
    op.drop_index("ix_integration_events_pending", table_name="integration_events")
    op.drop_constraint(
        "ck_integration_events_processing_state", "integration_events", type_="check"
    )
    op.drop_column("integration_events", "processing_state")
