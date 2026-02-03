"""Tests for threat report models."""

import pytest


class TestThreatReport:
    """Test ThreatReport model."""

    def test_valid_threat_report_creation(self):
        """Valid ThreatReport should be created successfully."""
        from src.models.enums import DataSource, ThreatLevel, TLPLevel
        from src.models.reports import ThreatReport

        report = ThreatReport(
            id="report-001",
            title="APT29 Campaign Analysis",
            description="Analysis of recent APT29 activity",
            source=DataSource.OTX,
            threat_level=ThreatLevel.HIGH,
            tlp=TLPLevel.AMBER,
        )

        assert report.id == "report-001"
        assert report.title == "APT29 Campaign Analysis"

    def test_title_max_length_200(self):
        """Title should reject strings over 200 chars."""
        from pydantic import ValidationError

        from src.models.enums import DataSource, ThreatLevel, TLPLevel
        from src.models.reports import ThreatReport

        with pytest.raises(ValidationError):
            ThreatReport(
                id="report-002",
                title="x" * 201,  # Too long
                source=DataSource.MANUAL,
                threat_level=ThreatLevel.LOW,
                tlp=TLPLevel.GREEN,
            )

    def test_tags_are_deduplicated_and_lowercase(self):
        """Tags should be deduplicated and normalized to lowercase."""
        from src.models.enums import DataSource, ThreatLevel, TLPLevel
        from src.models.reports import ThreatReport

        report = ThreatReport(
            id="report-003",
            title="Test Report",
            source=DataSource.MANUAL,
            threat_level=ThreatLevel.MEDIUM,
            tlp=TLPLevel.GREEN,
            tags=["APT", "apt", "Malware", "MALWARE", "apt"],
        )

        # Should be deduplicated and lowercase
        assert set(report.tags) == {"apt", "malware"}
