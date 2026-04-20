"""Add analysis_state, analysis_result, council_state, latest_council_note to sessions.

Revision ID: 002
Revises: 001
Create Date: 2026-04-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("sessions") as batch:
        batch.add_column(sa.Column("analysis_state", sa.String(), nullable=True))
        batch.add_column(sa.Column("analysis_result", sa.Text(), nullable=True))
        batch.add_column(sa.Column("council_state", sa.String(), nullable=True))
        batch.add_column(sa.Column("latest_council_note", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sessions") as batch:
        batch.drop_column("latest_council_note")
        batch.drop_column("council_state")
        batch.drop_column("analysis_result")
        batch.drop_column("analysis_state")
