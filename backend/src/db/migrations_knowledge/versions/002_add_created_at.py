"""Add created_at column to knowledge_resources.

Revision ID: 002
Revises: 001
Create Date: 2026-04-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "knowledge_resources",
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    # Backfill existing rows with last_updated value
    op.execute(
        "UPDATE knowledge_resources SET created_at = last_updated WHERE created_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("knowledge_resources", "created_at")
