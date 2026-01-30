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
