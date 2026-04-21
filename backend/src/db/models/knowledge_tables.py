"""SQLModel table models for knowledge.db."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class KnowledgeResourceTable(SQLModel, table=True):
    """One row per knowledge resource — replaces .md files on disk."""

    __tablename__ = "knowledge_resources"

    id: str = Field(primary_key=True)  # e.g. "geopolitical/norway_russia"
    category: str = Field(default="")  # e.g. "geopolitical"
    keywords: str = Field(default="[]")  # JSON array
    priority: int = Field(default=1)
    markdown_content: str = Field(default="")
    citation: str | None = Field(default=None)  # JSON
    created_at: datetime | None = Field(default=None)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PerspectiveDocumentTable(SQLModel, table=True):
    """One row per official government reference document, linked to a perspective."""

    __tablename__ = "perspective_documents"

    id: str = Field(primary_key=True)  # e.g. "us_nss_2022"
    perspective: str = Field(index=True)  # "us", "norway", "eu", "china", "russia"
    section: str = Field(index=True)  # "political", "economic", "military"
    title: str
    source: str | None = Field(default=None)  # e.g. "White House, 2022"
    date_published: datetime = Field(default_factory=lambda: datetime.now(UTC))
    markdown_content: str = Field(default="")
    is_active: bool = Field(default=True)
