from enum import Enum

from pydantic import BaseModel, Field

from src.models.enums import DataSource


class PMESIICategory(str, Enum):
    POLITICAL = "political"
    MILITARY = "military"
    ECONOMIC = "economic"
    SOCIAL = "social"
    INFORMATION = "information"
    INFRASTRUCTURE = "infrastructure"


class PMESIIEntity(BaseModel):
    id: str = Field(..., description="Unique identifier for this entity")
    name: str = Field(..., description="Short name or label for the entity")
    description: str = Field(
        ..., description="Factual description"
    )
    categories: list[PMESIICategory] = Field(
        ..., description="One or more PMESII categories"
    )
    sources: list[DataSource] = Field(
        ..., description="All sources that contrbuted to this entity"
    )
    confidence: int = Field(
        ..., ge=0, le=100, description="How well ths finding is supported (0-100)"
    )
    relevant_to: list[str] = Field(
        default_factory=list, description="PIR IDs this entity helps answer"
    )
    tags: list[str] = Field(
        default_factory=list, description="tags for relations and context"
    )
    first_observed: str | None = Field(
        default=None, description="ISO date when first observed"
    )
    last_updated: str | None = Field(
        default=None, description="ISO date when last updated"
    )


class ProcessingResult(BaseModel):
    entities: list[PMESIIEntity] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    processing_summary: str = Field(default="")
    assessment_changed: bool = Field(default=False)
    change_summary: str | None = Field(default=None)
