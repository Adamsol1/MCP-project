"""Enums for TI data models"""

from enum import Enum


class IOCType(str, Enum):
    """Types of Indicators of Compromise"""

    IPV4 = "ipv4"
    IPV6 = "ipv6"
    DOMAIN = "domain"
    URL = "url"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    EMAIL = "email"
    CVE = "cve"


class ThreatLevel(str, Enum):
    """Threat levels severity"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class TLPLevel(str, Enum):
    """Traffic Light Protocol for information sharing restrictions."""

    WHITE = "white"  # Public - unlimited sharing
    GREEN = "green"  # Community - share within community
    AMBER = "amber"  # Limited - share on need-to-know
    RED = "red"  # Restricted - named recipients only


class IndicatorRole(str, Enum):
    """What the indicator is used for in an attack."""

    C2 = "c2"  # Command and Control server
    MALWARE = "malware"  # Malware hash or delivery
    PHISHING = "phishing"  # Phishing domain/URL
    SCANNER = "scanner"  # Scanning/reconnaissance
    EXFILTRATION = "exfiltration"  # Data exfiltration endpoint
    UNKNOWN = "unknown"  # Not yet classified


class DataSource(str, Enum):
    """Where threat intelligence data originated."""

    OTX = "otx"  # AlienVault OTX
    MISP = "misp"  # MISP platform
    CSV_UPLOAD = "csv_upload"
    PDF_UPLOAD = "pdf_upload"
    TXT_UPLOAD = "txt_upload"
    JSON_UPLOAD = "json_upload"
    MANUAL = "manual"  # Manual entry


class ExtractionMethod(str, Enum):
    """How IOCs were extracted from source data."""

    DIRECT_PARSE = "direct_parse"  # Structured data (JSON, CSV)
    REGEX = "regex"  # Pattern matching
    AI_EXTRACTION = "ai_extraction"  # LLM-based extraction
    MANUAL = "manual"  # Human entry


class ProcessingStatus(str, Enum):
    """State machine for file processing."""

    PENDING = "pending"  # Waiting to be processed
    PROCESSING = "processing"  # Currently being processed
    COMPLETED = "completed"  # Successfully processed
    FAILED = "failed"  # Processing failed
