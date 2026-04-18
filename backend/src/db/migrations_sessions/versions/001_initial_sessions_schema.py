"""Initial sessions.db schema.

Revision ID: 001
Revises:
Create Date: 2026-04-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "direction_state", sa.String(), nullable=False, server_default="initial"
        ),
        sa.Column("direction_context", sa.Text(), nullable=True),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_pir", sa.Text(), nullable=True),
        sa.Column("pending_reasoning_log_direction", sa.Text(), nullable=True),
        sa.Column("collection_state", sa.String(), nullable=True),
        sa.Column("pir", sa.Text(), nullable=True),
        sa.Column("collection_plan", sa.Text(), nullable=True),
        sa.Column("selected_sources", sa.Text(), nullable=True),
        sa.Column("pending_reasoning_log_collection", sa.Text(), nullable=True),
        sa.Column("gather_more_feedback", sa.Text(), nullable=True),
        sa.Column("processing_state", sa.String(), nullable=True),
        sa.Column("pending_reasoning_log_processing", sa.Text(), nullable=True),
        sa.Column("sub_state", sa.String(), nullable=True),
    )

    op.create_table(
        "collection_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(),
            sa.ForeignKey("sessions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("pir", sa.Text(), nullable=False, server_default=""),
        sa.Column("raw_response", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "processing_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(),
            sa.ForeignKey("sessions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("pir", sa.Text(), nullable=False, server_default=""),
        sa.Column("raw_result", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(),
            sa.ForeignKey("sessions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("original_filename", sa.String(), nullable=False, server_default=""),
        sa.Column("filename", sa.String(), nullable=False, server_default=""),
        sa.Column("stored_filename", sa.String(), nullable=False, server_default=""),
        sa.Column("stored_path", sa.String(), nullable=False, server_default=""),
        sa.Column("extension", sa.String(), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(), nullable=False, server_default=""),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column(
            "parse_status", sa.String(), nullable=False, server_default="pending"
        ),
        sa.Column("searchable", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("search_skip_reason", sa.String(), nullable=True),
        sa.Column("parsed_content", sa.Text(), nullable=True),
        sa.Column("parsed_markdown_path", sa.String(), nullable=True),
        sa.Column("citation", sa.Text(), nullable=True),
        sa.Column("metadata_flags", sa.Text(), nullable=True),
    )

    op.create_table(
        "analysis_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(),
            sa.ForeignKey("sessions.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("processing_result", sa.Text(), nullable=True),
        sa.Column("analysis_draft", sa.Text(), nullable=True),
        sa.Column("latest_council_note", sa.Text(), nullable=True),
    )

    op.create_table(
        "research_log_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(),
            sa.ForeignKey("sessions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("entry_type", sa.String(), nullable=False, server_default=""),
        sa.Column("phase", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default="{}"),
    )

    op.create_table(
        "collection_status",
        sa.Column("session_id", sa.String(), primary_key=True),
        sa.Column("status", sa.String(), nullable=False, server_default="collecting"),
        sa.Column("current_source", sa.String(), nullable=True),
        sa.Column("current_activity", sa.String(), nullable=True),
        sa.Column("sources", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("collection_status")
    op.drop_table("research_log_entries")
    op.drop_table("analysis_sessions")
    op.drop_table("uploaded_files")
    op.drop_table("processing_attempts")
    op.drop_table("collection_attempts")
    op.drop_table("sessions")
