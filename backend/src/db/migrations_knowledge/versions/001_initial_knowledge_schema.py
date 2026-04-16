"""Initial knowledge.db schema.

Revision ID: 001
Revises:
Create Date: 2026-04-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_resources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("category", sa.String(), nullable=False, server_default=""),
        sa.Column("keywords", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("markdown_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("citation", sa.Text(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("knowledge_resources")
