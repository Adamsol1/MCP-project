"""Threat Intelligence Data Models.

This package contains all Pydantic models for the MCP Threat Intelligence system.

Usage:
    from src.models import NormalizedIndicator, ThreatReport, IOCType
    from src.models.sources import OTXPulse, MISPEvent
"""

from src.models.enums import (
    DataSource,
    ExtractionMethod,
    IndicatorRole,
    IOCType,
    ProcessingStatus,
    ThreatLevel,
    TLPLevel,
)
from src.models.extraction import (
    ExtractedContent,
    PDFExtractedContent,
    RawIOC,
)
from src.models.indicators import NormalizedIndicator
from src.models.reports import ThreatReport

__all__ = [
    # Enums
    "IOCType",
    "ThreatLevel",
    "TLPLevel",
    "IndicatorRole",
    "DataSource",
    "ExtractionMethod",
    "ProcessingStatus",
    # Extraction
    "RawIOC",
    "ExtractedContent",
    "PDFExtractedContent",
    # Indicators
    "NormalizedIndicator",
    # Reports
    "ThreatReport",
]
