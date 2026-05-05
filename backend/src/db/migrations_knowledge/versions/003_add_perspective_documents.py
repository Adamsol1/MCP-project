"""Add perspective_documents table.

Revision ID: 003
Revises: 002
Create Date: 2026-04-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = sa.inspect(bind).get_table_names()
    if "perspective_documents" in existing:
        return
    op.create_table(
        "perspective_documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("perspective", sa.String(), nullable=False, index=True),
        sa.Column("section", sa.String(), nullable=False, index=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("date_published", sa.DateTime(), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_table("perspective_documents")
