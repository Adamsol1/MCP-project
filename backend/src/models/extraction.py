"""Models for extracted content from files."""

from pydantic import BaseModel, Field

from src.models.enums import IOCType


class RawIOC(BaseModel):
    """A raw IOC extracted from a file before normalization.
    This represents an IOC as it was found in the source,
    before validation and normalization.
    """

    raw_value: str = Field(..., description="Raw IOC value as extracted")

    suspected_type: IOCType = Field(..., description="Suspected IOC type")

    context: str | None = Field(
        default=None, max_length=500, description="Context where IOC was found"
    )

    line_number: int | None = Field(
        default=None, ge=1, description="Line number where IOC was found"
    )

    extraction_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0"
    )
