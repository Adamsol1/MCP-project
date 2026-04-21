"""SQLModel table definitions for sessions.db and knowledge.db."""

from src.db.models.knowledge_tables import KnowledgeResourceTable
from src.db.models.session_tables import (
    AnalysisSessionTable,
    CollectionAttemptTable,
    CollectionStatusTable,
    ProcessingAttemptTable,
    ResearchLogEntryTable,
    SessionTable,
    UploadedFileTable,
)

__all__ = [
    "SessionTable",
    "CollectionAttemptTable",
    "ProcessingAttemptTable",
    "UploadedFileTable",
    "AnalysisSessionTable",
    "ResearchLogEntryTable",
    "CollectionStatusTable",
    "KnowledgeResourceTable",
]
