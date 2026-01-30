"""Models for extracted content from files."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.models.enums import ExtractionMethod, IOCType


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


class ExtractedContent(BaseModel):
    """Content extracted from an uploaded file."""

    file_upload_id: str = Field(..., description="Reference to the source file upload")

    extracted_at: datetime = Field(..., description="When extraction occurred")

    extraction_method: ExtractionMethod = Field(
        ..., description="How the content was extracted"
    )

    raw_iocs: list[RawIOC] = Field(
        default_factory=list, description="List of extracted raw IOCs"
    )

    raw_text: str | None = Field(default=None, description="Raw text for AI processing")

    detected_schema: dict[str, Any] | None = Field(
        default=None, description="Detected schema for JSON sources"
    )

    source_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional source metadata"
    )

    extraction_errors: list[str] = Field(
        default_factory=list, description="Errors encountered during extraction"
    )


class PDFExtractedContent(ExtractedContent):
    """Extracted content from PDF files with PDF-specific metadata."""

    page_count: int = Field(..., ge=1, description="Number of pages in the PDF")

    ocr_applied: bool = Field(
        default=False, description="Whether OCR was used to extract text"
    )

    document_title: str | None = Field(
        default=None, description="PDF document title from metadata"
    )

    document_author: str | None = Field(
        default=None, description="PDF document author from metadata"
    )
