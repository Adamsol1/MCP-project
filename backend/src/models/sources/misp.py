"""Models for MISP (Malware Information Sharing Platform) data.

MISP is an open-source threat intelligence platform. Data is organized into
"Events" which contain multiple "Attributes" (indicators).

API Reference: https://www.misp-project.org/documentation/
"""

from datetime import datetime

from pydantic import BaseModel, Field


class MISPAttribute(BaseModel):
    """A MISP Attribute (indicator).

    Attributes are the core data points in MISP, representing
    individual indicators of compromise.
    """

    id: str | None = Field(default=None, description="Attribute ID")

    event_id: str | None = Field(
        default=None, description="Parent event ID"
    )

    type: str = Field(..., description="MISP attribute type (ip-dst, domain, md5, etc.)")

    category: str = Field(
        default="External analysis",
        description="Attribute category (Network activity, Payload delivery, etc.)"
    )

    value: str = Field(..., description="The IOC value")

    to_ids: bool = Field(
        default=True,
        description="Whether this attribute should be used for IDS detection"
    )

    comment: str | None = Field(default=None, description="Attribute comment")

    timestamp: datetime | None = Field(
        default=None, description="Attribute timestamp"
    )

    distribution: int = Field(
        default=0,
        ge=0,
        le=5,
        description="Distribution level (0=org, 1=community, 2=connected, 3=all, 4=sharing group, 5=inherit)"
    )

    first_seen: datetime | None = Field(
        default=None, description="First seen timestamp"
    )

    last_seen: datetime | None = Field(
        default=None, description="Last seen timestamp"
    )

    deleted: bool = Field(default=False, description="Whether attribute is deleted")

    disable_correlation: bool = Field(
        default=False, description="Whether to disable correlation"
    )


class MISPEvent(BaseModel):
    """A MISP Event containing threat intelligence.

    Events are MISP's primary container for threat intelligence,
    grouping related attributes together.
    """

    id: str | None = Field(default=None, description="Event ID")

    uuid: str | None = Field(default=None, description="Event UUID")

    info: str = Field(..., description="Event title/description")

    threat_level_id: int = Field(
        default=4,
        ge=1,
        le=4,
        description="Threat level (1=High, 2=Medium, 3=Low, 4=Undefined)"
    )

    analysis: int = Field(
        default=0,
        ge=0,
        le=2,
        description="Analysis state (0=Initial, 1=Ongoing, 2=Complete)"
    )

    date: str | None = Field(default=None, description="Event date (YYYY-MM-DD)")

    timestamp: datetime | None = Field(
        default=None, description="Event timestamp"
    )

    publish_timestamp: datetime | None = Field(
        default=None, description="When event was published"
    )

    org_id: str | None = Field(default=None, description="Organization ID")

    orgc_id: str | None = Field(default=None, description="Creator organization ID")

    distribution: int = Field(
        default=0,
        ge=0,
        le=4,
        description="Distribution level"
    )

    published: bool = Field(default=False, description="Whether event is published")

    attribute_count: int = Field(
        default=0, ge=0, description="Number of attributes"
    )

    attributes: list[MISPAttribute] = Field(
        default_factory=list, description="Event attributes"
    )

    tags: list[str] = Field(default_factory=list, description="Event tags")

    extends_uuid: str | None = Field(
        default=None, description="UUID of event this extends"
    )
