from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_0006"
down_revision: str | Sequence[str] | None = "20261120_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "community_servers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "community_id",
            sa.Uuid(),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("host", sa.String(253), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.UniqueConstraint("community_id", "host", "port", name="uq_community_servers_endpoint"),
        sa.CheckConstraint("port BETWEEN 1 AND 65535", name="ck_community_servers_port"),
    )


def downgrade() -> None:
    op.drop_table("community_servers")
