"""Models for AlienVault OTX (Open Threat Exchange) data.

OTX is a threat intelligence sharing platform. Data is organized into "Pulses"
which contain multiple indicators.

API Reference: https://otx.alienvault.com/api
"""

from datetime import datetime

from pydantic import BaseModel, Field


class OTXIndicator(BaseModel):
    """An indicator from an OTX Pulse.

    Maps to OTX API indicator structure.
    """

    indicator: str = Field(..., description="The IOC value")

    type: str = Field(..., description="OTX indicator type (IPv4, domain, URL, etc.)")

    created: datetime | None = Field(
        default=None, description="When indicator was created"
    )

    is_active: bool = Field(default=True, description="Whether indicator is active")

    role: str | None = Field(
        default=None, description="Role of indicator (e.g., C2, payload delivery)"
    )

    title: str | None = Field(default=None, description="Indicator title")

    description: str | None = Field(default=None, description="Indicator description")

    expiration: datetime | None = Field(
        default=None, description="When indicator expires"
    )

    content: str | None = Field(
        default=None, description="Additional content/context"
    )


class OTXPulse(BaseModel):
    """An OTX Pulse containing threat intelligence.

    A Pulse is OTX's primary unit of threat intelligence,
    containing multiple indicators and metadata.
    """

    id: str = Field(..., description="Pulse ID")

    name: str = Field(..., description="Pulse name/title")

    description: str | None = Field(default=None, description="Pulse description")

    author_name: str | None = Field(default=None, description="Pulse author")

    created: datetime | None = Field(default=None, description="Creation timestamp")

    modified: datetime | None = Field(
        default=None, description="Last modification timestamp"
    )

    tlp: str | None = Field(
        default=None, description="Traffic Light Protocol level"
    )

    adversary: str | None = Field(
        default=None, description="Attributed threat actor"
    )

    targeted_countries: list[str] = Field(
        default_factory=list, description="Targeted country codes"
    )

    malware_families: list[str] = Field(
        default_factory=list, description="Related malware families"
    )

    attack_ids: list[str] = Field(
        default_factory=list, description="MITRE ATT&CK technique IDs"
    )

    industries: list[str] = Field(
        default_factory=list, description="Targeted industries"
    )

    tags: list[str] = Field(default_factory=list, description="Pulse tags")

    references: list[str] = Field(
        default_factory=list, description="External references"
    )

    indicators: list[OTXIndicator] = Field(
        default_factory=list, description="Indicators in this pulse"
    )

    revision: int = Field(default=1, description="Pulse revision number")

    public: bool = Field(default=True, description="Whether pulse is public")
