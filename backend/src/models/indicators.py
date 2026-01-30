"""Models for normalized threat indicators.

This module contains the NormalizedIndicator model which represents a validated,
normalized Indicator of Compromise (IOC). The model validates that IOC values
match their declared types using regex patterns and the ipaddress library.

Components Summary:
|------------------------|-----------|---------------------------------------------|
| Component              | Type      | Purpose                                     |
|------------------------|-----------|---------------------------------------------|
| NormalizedIndicator    | Class     | Main model for validated IOCs               |
| id                     | Field     | Unique identifier for the indicator         |
| type                   | Field     | IOC type (determines which validator runs)  |
| value                  | Field     | The actual IOC (IP, hash, domain, etc.)     |
| confidence             | Field     | 0-100 score of how reliable this IOC is     |
| threat_level           | Field     | Severity (critical/high/medium/low/unknown) |
| source                 | Field     | Where data came from (OTX, MISP, manual)    |
| @model_validator       | Decorator | Runs after fields are set, triggers valid.  |
| _validate_ipv4         | Method    | Uses ipaddress library to validate IPv4     |
| _validate_ipv6         | Method    | Uses ipaddress library to validate IPv6     |
| _validate_md5          | Method    | Regex: 32 hex characters                    |
| _validate_sha1         | Method    | Regex: 40 hex characters                    |
| _validate_sha256       | Method    | Regex: 64 hex characters                    |
| _validate_domain       | Method    | Regex: valid domain format                  |
| _validate_url          | Method    | Must start with http:// or https://         |
| _validate_email        | Method    | Regex: basic email format                   |
| _validate_cve          | Method    | Regex: CVE-YYYY-NNNN+ format                |
|------------------------|-----------|---------------------------------------------|

Validation Patterns:
--------------------
- MD5:    ^[a-f0-9]{32}$
- SHA1:   ^[a-f0-9]{40}$
- SHA256: ^[a-f0-9]{64}$
- Domain: ^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,}$
- CVE:    ^cve-\\d{4}-\\d{4,}$
- Email:  ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$
"""

import ipaddress
import re
from typing import Self

from pydantic import BaseModel, Field, model_validator

from src.models.enums import (
    DataSource,
    IOCType,
    ThreatLevel,
)


class NormalizedIndicator(BaseModel):
    """A validated, normalized Indicator of Compromise."""

    id: str = Field(..., description="Unique identifier")

    type: IOCType = Field(..., description="Type of IOC")

    value: str = Field(..., description="The IOC value (validated per type)")

    confidence: int = Field(..., ge=0, le=100, description="Confidence score 0-100")

    threat_level: ThreatLevel = Field(..., description="Severity level")

    source: DataSource = Field(..., description="Where this IOC came from")

    @model_validator(mode="after")
    def validate_value_matches_type(self) -> Self:
        """Validate that the value format matches the IOC type."""
        validators = {
            IOCType.IPV4: self._validate_ipv4,
            IOCType.IPV6: self._validate_ipv6,
            IOCType.MD5: self._validate_md5,
            IOCType.SHA1: self._validate_sha1,
            IOCType.SHA256: self._validate_sha256,
            IOCType.DOMAIN: self._validate_domain,
            IOCType.URL: self._validate_url,
            IOCType.EMAIL: self._validate_email,
            IOCType.CVE: self._validate_cve,
        }

        validator = validators.get(self.type)
        if validator:
            validator(self.value)

        return self

    def _validate_ipv4(self, value: str) -> None:
        """Validate IPv4 address."""
        try:
            addr = ipaddress.ip_address(value)
            if not isinstance(addr, ipaddress.IPv4Address):
                raise ValueError(f"Not an IPv4 address: {value}")
        except ValueError as e:
            raise ValueError(f"Invalid IPv4 address: {value}") from e

    def _validate_ipv6(self, value: str) -> None:
        """Validate IPv6 address."""
        try:
            addr = ipaddress.ip_address(value)
            if not isinstance(addr, ipaddress.IPv6Address):
                raise ValueError(f"Not an IPv6 address: {value}")
        except ValueError as e:
            raise ValueError(f"Invalid IPv6 address: {value}") from e

    def _validate_md5(self, value: str) -> None:
        """Validate MD5 hash (32 hex chars)."""
        if not re.match(r"^[a-f0-9]{32}$", value.lower()):
            raise ValueError(f"Invalid MD5 hash: {value}")

    def _validate_sha1(self, value: str) -> None:
        """Validate SHA1 hash (40 hex chars)."""
        if not re.match(r"^[a-f0-9]{40}$", value.lower()):
            raise ValueError(f"Invalid SHA1 hash: {value}")

    def _validate_sha256(self, value: str) -> None:
        """Validate SHA256 hash (64 hex chars)."""
        if not re.match(r"^[a-f0-9]{64}$", value.lower()):
            raise ValueError(f"Invalid SHA256 hash: {value}")

    def _validate_domain(self, value: str) -> None:
        """Validate domain name."""
        pattern = r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$"
        if not re.match(pattern, value.lower()):
            raise ValueError(f"Invalid domain: {value}")

    def _validate_url(self, value: str) -> None:
        """Validate URL (basic check)."""
        if not value.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL (must start with http/https): {value}")

    def _validate_email(self, value: str) -> None:
        """Validate email address."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, value):
            raise ValueError(f"Invalid email: {value}")

    def _validate_cve(self, value: str) -> None:
        """Validate CVE ID."""
        if not re.match(r"^cve-\d{4}-\d{4,}$", value.lower()):
            raise ValueError(f"Invalid CVE: {value}")
