"""Tests for indicator models."""

import pytest


class TestNormalizedIndicator:
    """Test NormalizedIndicator model."""

    def test_valid_ipv4_indicator(self):
        """Valid IPv4 indicator should be created."""

        from src.models.enums import DataSource, IOCType, ThreatLevel
        from src.models.indicators import NormalizedIndicator

        indicator = NormalizedIndicator(
            id="ind-001",
            type=IOCType.IPV4,
            value="192.168.1.1",
            confidence=85,
            threat_level=ThreatLevel.HIGH,
            source=DataSource.OTX,
        )

        assert indicator.value == "192.168.1.1"
        assert indicator.type == IOCType.IPV4

    def test_invalid_ipv4_rejected(self):
        """Invalid IPv4 should raise ValidationError."""
        from pydantic import ValidationError

        from src.models.enums import DataSource, IOCType, ThreatLevel
        from src.models.indicators import NormalizedIndicator

        with pytest.raises(ValidationError):
            NormalizedIndicator(
                id="ind-002",
                type=IOCType.IPV4,
                value="not-an-ip",  # Invalid
                confidence=50,
                threat_level=ThreatLevel.MEDIUM,
                source=DataSource.MANUAL,
            )
