"""SQLModel table models for sessions.db.

Every complex nested object (DialogueContext, ReasoningLog, etc.) is stored
as a JSON TEXT column to avoid deep normalization and preserve compatibility
with existing Pydantic models.
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class SessionTable(SQLModel, table=True):
    """One row per intelligence session — stores all three flow states."""

    __tablename__ = "sessions"

    id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Direction flow state
    direction_state: str = Field(default="initial")
    direction_context: str | None = Field(default=None)  # JSON
    question_count: int = Field(default=0)
    current_pir: str | None = Field(default=None)  # JSON string
    pending_reasoning_log_direction: str | None = Field(default=None)  # JSON

    # Collection flow state
    collection_state: str | None = Field(default=None)
    pir: str | None = Field(default=None)  # PIR text for collection/processing
    collection_plan: str | None = Field(default=None)
    selected_sources: str | None = Field(default=None)  # JSON array
    pending_reasoning_log_collection: str | None = Field(default=None)  # JSON
    gather_more_feedback: str | None = Field(default=None)

    # Processing flow state
    processing_state: str | None = Field(default=None)
    pending_reasoning_log_processing: str | None = Field(default=None)  # JSON

    # Analysis flow state
    analysis_state: str | None = Field(default=None)
    analysis_result: str | None = Field(default=None)  # JSON

    # Council flow state
    council_state: str | None = Field(default=None)
    latest_council_note: str | None = Field(default=None)  # JSON

    # Shared
    sub_state: str | None = Field(default=None)


class CollectionAttemptTable(SQLModel, table=True):
    """One row per raw collection agent response."""

    __tablename__ = "collection_attempts"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, foreign_key="sessions.id")
    attempt_number: int = Field(default=1)
    pir: str = Field(default="")
    raw_response: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProcessingAttemptTable(SQLModel, table=True):
    """One row per processing agent result."""

    __tablename__ = "processing_attempts"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, foreign_key="sessions.id")
    attempt_number: int = Field(default=1)
    pir: str = Field(default="")
    raw_result: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UploadedFileTable(SQLModel, table=True):
    """Metadata + parsed text content for an uploaded file."""

    __tablename__ = "uploaded_files"

    id: str = Field(primary_key=True)  # file_upload_id UUID
    session_id: str = Field(index=True, foreign_key="sessions.id")
    original_filename: str = Field(default="")
    filename: str = Field(default="")
    stored_filename: str = Field(default="")
    stored_path: str = Field(default="")
    extension: str = Field(default="")
    mime_type: str | None = Field(default=None)
    size_bytes: int = Field(default=0)
    sha256: str = Field(default="")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    parse_status: str = Field(default="pending")
    searchable: bool = Field(default=False)
    search_skip_reason: str | None = Field(default=None)
    parsed_content: str | None = Field(default=None)  # Full parsed markdown
    parsed_markdown_path: str | None = Field(default=None)
    citation: str | None = Field(default=None)  # JSON
    metadata_flags: str | None = Field(default=None)  # JSON array


class AnalysisSessionTable(SQLModel, table=True):
    """Persisted analysis state — processing result, draft, council note."""

    __tablename__ = "analysis_sessions"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True, foreign_key="sessions.id")
    processing_result: str | None = Field(default=None)  # JSON
    analysis_draft: str | None = Field(default=None)  # JSON
    latest_council_note: str | None = Field(default=None)  # JSON


class ResearchLogEntryTable(SQLModel, table=True):
    """One row per research/reasoning log entry (replaces JSONL files)."""

    __tablename__ = "research_log_entries"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, foreign_key="sessions.id")
    entry_type: str = Field(
        default=""
    )  # "ai_generation", "user_action", "reasoning_log"
    phase: str | None = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content: str = Field(default="{}")  # JSON blob of the full entry


class CollectionStatusTable(SQLModel, table=True):
    """Live collection progress — polled by frontend."""

    __tablename__ = "collection_status"

    session_id: str = Field(primary_key=True)
    status: str = Field(default="collecting")
    current_source: str | None = Field(default=None)
    current_activity: str | None = Field(default=None)
    sources: str = Field(default="{}")  # JSON dict of per-source counts
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
