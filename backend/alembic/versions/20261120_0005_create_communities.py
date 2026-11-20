from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_0005"
down_revision: str | Sequence[str] | None = "20261120_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "communities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
    )
    op.create_index("ix_communities_owner_id", "communities", ["owner_id"])
    op.create_table(
        "community_memberships",
        sa.Column(
            "community_id",
            sa.Uuid(),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    op.create_index("ix_community_memberships_user_id", "community_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_table("community_memberships")
    op.drop_table("communities")
