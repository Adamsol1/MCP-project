"""SQLModel table model for knowledge.db."""

from datetime import datetime, UTC
from typing import Optional

from sqlmodel import Field, SQLModel


class KnowledgeResourceTable(SQLModel, table=True):
    """One row per knowledge resource — replaces .md files on disk."""

    __tablename__ = "knowledge_resources"

    id: str = Field(primary_key=True)  # e.g. "geopolitical/norway_russia"
    category: str = Field(default="")  # e.g. "geopolitical"
    keywords: str = Field(default="[]")  # JSON array
    priority: int = Field(default=1)
    markdown_content: str = Field(default="")
    citation: Optional[str] = Field(default=None)  # JSON
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
