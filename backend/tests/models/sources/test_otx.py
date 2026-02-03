"""Tests for OTX (AlienVault Open Threat Exchange) models."""

from datetime import datetime


class TestOTXIndicator:
    """Test OTXIndicator model."""

    def test_valid_otx_indicator_creation(self):
        """Valid OTXIndicator should be created successfully."""
        from src.models.sources.otx import OTXIndicator

        indicator = OTXIndicator(
            indicator="192.168.1.1",
            type="IPv4",
            is_active=True,
            role="C2",
        )

        assert indicator.indicator == "192.168.1.1"
        assert indicator.type == "IPv4"
        assert indicator.is_active is True

    def test_otx_indicator_with_all_fields(self):
        """OTXIndicator with all optional fields."""
        from src.models.sources.otx import OTXIndicator

        now = datetime.now()
        indicator = OTXIndicator(
            indicator="malware.example.com",
            type="domain",
            created=now,
            is_active=True,
            role="payload_delivery",
            title="Malware Domain",
            description="Known malware distribution domain",
            expiration=now,
            content="Additional context here",
        )

        assert indicator.title == "Malware Domain"
        assert indicator.description == "Known malware distribution domain"


class TestOTXPulse:
    """Test OTXPulse model."""

    def test_valid_otx_pulse_creation(self):
        """Valid OTXPulse should be created successfully."""
        from src.models.sources.otx import OTXPulse

        pulse = OTXPulse(
            id="pulse-123",
            name="APT29 Campaign Analysis",
        )

        assert pulse.id == "pulse-123"
        assert pulse.name == "APT29 Campaign Analysis"
        assert pulse.indicators == []

    def test_otx_pulse_with_indicators(self):
        """OTXPulse with nested indicators."""
        from src.models.sources.otx import OTXIndicator, OTXPulse

        indicator1 = OTXIndicator(indicator="10.0.0.1", type="IPv4")
        indicator2 = OTXIndicator(indicator="evil.com", type="domain")

        pulse = OTXPulse(
            id="pulse-456",
            name="Test Pulse",
            description="Test description",
            indicators=[indicator1, indicator2],
            tags=["apt", "malware"],
            targeted_countries=["US", "GB"],
            malware_families=["Emotet"],
        )

        assert len(pulse.indicators) == 2
        assert pulse.indicators[0].indicator == "10.0.0.1"
        assert set(pulse.tags) == {"apt", "malware"}
        assert "Emotet" in pulse.malware_families

    def test_otx_pulse_with_metadata(self):
        """OTXPulse with full metadata."""
        from src.models.sources.otx import OTXPulse

        now = datetime.now()
        pulse = OTXPulse(
            id="pulse-789",
            name="Full Metadata Pulse",
            description="Detailed threat analysis",
            author_name="Security Team",
            created=now,
            modified=now,
            tlp="amber",
            adversary="APT29",
            attack_ids=["T1566", "T1059.001"],
            industries=["Finance", "Healthcare"],
            references=["https://example.com/report"],
            revision=3,
            public=False,
        )

        assert pulse.author_name == "Security Team"
        assert pulse.adversary == "APT29"
        assert len(pulse.attack_ids) == 2
        assert pulse.public is False
