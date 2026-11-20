from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_0009"
down_revision: str | Sequence[str] | None = "20261120_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "community_posts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "community_id",
            sa.Uuid(),
            sa.ForeignKey("communities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("image", sa.LargeBinary()),
        sa.Column("image_type", sa.String(16)),
        sa.CheckConstraint(
            "(image IS NULL AND image_type IS NULL) OR "
            "(image IS NOT NULL AND image_type IS NOT NULL "
            "AND octet_length(image) BETWEEN 1 AND 2097152 "
            "AND image_type IN ('image/png', 'image/jpeg', 'image/webp'))",
            name="ck_community_posts_image",
        ),
    )
    op.create_index(
        "ix_community_posts_date", "community_posts", ["community_id", "created_at", "id"]
    )


def downgrade() -> None:
    op.drop_table("community_posts")
