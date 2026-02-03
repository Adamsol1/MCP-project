"""Tests for MISP (Malware Information Sharing Platform) models."""

import pytest
from datetime import datetime


class TestMISPAttribute:
    """Test MISPAttribute model."""

    def test_valid_misp_attribute_creation(self):
        """Valid MISPAttribute should be created successfully."""
        from src.models.sources.misp import MISPAttribute

        attribute = MISPAttribute(
            type="ip-dst",
            value="192.168.1.1",
        )

        assert attribute.type == "ip-dst"
        assert attribute.value == "192.168.1.1"
        assert attribute.to_ids is True  # Default

    def test_misp_attribute_with_all_fields(self):
        """MISPAttribute with all optional fields."""
        from src.models.sources.misp import MISPAttribute

        now = datetime.now()
        attribute = MISPAttribute(
            id="attr-123",
            event_id="event-456",
            type="domain",
            category="Network activity",
            value="malware.example.com",
            to_ids=True,
            comment="Known C2 domain",
            timestamp=now,
            distribution=1,
            first_seen=now,
            last_seen=now,
            deleted=False,
            disable_correlation=False,
        )

        assert attribute.id == "attr-123"
        assert attribute.category == "Network activity"
        assert attribute.comment == "Known C2 domain"

    def test_misp_attribute_distribution_validation(self):
        """Distribution must be 0-5."""
        from src.models.sources.misp import MISPAttribute
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MISPAttribute(
                type="ip-dst",
                value="10.0.0.1",
                distribution=10,  # Invalid: > 5
            )


class TestMISPEvent:
    """Test MISPEvent model."""

    def test_valid_misp_event_creation(self):
        """Valid MISPEvent should be created successfully."""
        from src.models.sources.misp import MISPEvent

        event = MISPEvent(
            info="Phishing Campaign Targeting Finance Sector",
        )

        assert event.info == "Phishing Campaign Targeting Finance Sector"
        assert event.attributes == []
        assert event.threat_level_id == 4  # Default: Undefined

    def test_misp_event_with_attributes(self):
        """MISPEvent with nested attributes."""
        from src.models.sources.misp import MISPEvent, MISPAttribute

        attr1 = MISPAttribute(type="ip-dst", value="10.0.0.1")
        attr2 = MISPAttribute(type="domain", value="phishing.example.com")

        event = MISPEvent(
            id="event-123",
            uuid="550e8400-e29b-41d4-a716-446655440000",
            info="Test Event",
            threat_level_id=1,  # High
            analysis=2,  # Complete
            attributes=[attr1, attr2],
            tags=["phishing", "finance"],
        )

        assert len(event.attributes) == 2
        assert event.threat_level_id == 1
        assert event.analysis == 2

    def test_misp_event_with_full_metadata(self):
        """MISPEvent with full metadata."""
        from src.models.sources.misp import MISPEvent

        now = datetime.now()
        event = MISPEvent(
            id="event-456",
            uuid="550e8400-e29b-41d4-a716-446655440001",
            info="Full Metadata Event",
            threat_level_id=2,  # Medium
            analysis=1,  # Ongoing
            date="2024-01-15",
            timestamp=now,
            publish_timestamp=now,
            org_id="org-1",
            orgc_id="org-2",
            distribution=2,
            published=True,
            attribute_count=5,
            extends_uuid="550e8400-e29b-41d4-a716-446655440002",
        )

        assert event.org_id == "org-1"
        assert event.published is True
        assert event.attribute_count == 5

    def test_misp_event_threat_level_validation(self):
        """Threat level must be 1-4."""
        from src.models.sources.misp import MISPEvent
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MISPEvent(
                info="Invalid Event",
                threat_level_id=0,  # Invalid: < 1
            )

    def test_misp_event_analysis_validation(self):
        """Analysis must be 0-2."""
        from src.models.sources.misp import MISPEvent
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MISPEvent(
                info="Invalid Event",
                analysis=5,  # Invalid: > 2
            )
