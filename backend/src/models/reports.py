"""Models for threat intelligence reports."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator

from src.models.enums import DataSource, ThreatLevel, TLPLevel
from src.models.indicators import NormalizedIndicator


class ThreatReport(BaseModel):
    """A threat intelligence report aggregating multiple indicators."""

    id: str = Field(..., description="Unique identifier")

    title: str = Field(..., max_length=200, description="Report title")

    description: str | None = Field(
        default=None, max_length=2000, description="Report description"
    )

    source: DataSource = Field(..., description="Where report came from")

    source_id: str | None = Field(default=None, description="ID from original source")

    source_url: str | None = Field(default=None, description="URL to original report")

    threat_level: ThreatLevel = Field(..., description="Overall severity")

    tlp: TLPLevel = Field(..., description="Sharing restrictions")

    tags: list[str] = Field(
        default_factory=list, description="Tags (deduplicated, lowercase)"
    )

    mitre_attack_ids: list[str] = Field(
        default_factory=list, description="MITRE ATT&CK IDs"
    )

    targeted_countries: list[str] = Field(
        default_factory=list, description="ISO alpha-2 country codes"
    )

    malware_families: list[str] = Field(
        default_factory=list, description="Malware family names"
    )

    threat_actors: list[str] = Field(
        default_factory=list, description="Threat actor names"
    )

    indicators: list[NormalizedIndicator] = Field(
        default_factory=list, description="IOCs in this report"
    )

    created_at: datetime = Field(
        default_factory=datetime.now, description="When report was created"
    )

    updated_at: datetime | None = Field(
        default=None, description="When report was last updated"
    )

    references: list[str] = Field(
        default_factory=list, description="External reference URLs"
    )

    file_upload_id: str | None = Field(
        default=None, description="Link to source file upload"
    )

    @model_validator(mode="after")
    def normalize_tags(self) -> Self:
        """Deduplicate and lowercase tags."""
        if self.tags:
            # Lowercase and deduplicate while preserving order
            seen = set()
            normalized = []
            for tag in self.tags:
                lower_tag = tag.lower()
                if lower_tag not in seen:
                    seen.add(lower_tag)
                    normalized.append(lower_tag)
            self.tags = normalized
        return self
