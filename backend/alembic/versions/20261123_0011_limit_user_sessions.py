from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261123_0011"
down_revision: str | Sequence[str] | None = "20261120_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_index(
        "ix_user_sessions_revoked",
        "user_sessions",
        ["token_hash"],
        postgresql_where=sa.text("revoked_at IS NOT NULL"),
    )
    op.execute("""
        WITH ranked AS (
            SELECT token_hash, row_number() OVER (
                PARTITION BY user_id ORDER BY expires_at DESC, token_hash DESC
            ) AS position
            FROM user_sessions
            WHERE revoked_at IS NULL AND expires_at > now()
        )
        DELETE FROM user_sessions USING ranked
        WHERE user_sessions.token_hash = ranked.token_hash AND ranked.position > 5
    """)


def downgrade() -> None:
    # Завершённые при обновлении сессии остаются недействительными после отката.
    op.drop_index("ix_user_sessions_revoked", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
