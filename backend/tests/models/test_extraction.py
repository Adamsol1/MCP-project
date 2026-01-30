"""TEsts for extraction models."""

import pytest


class TestRawIOC:
    """Test RawIOC model for raw extracted indicators."""

    def test_valid_raw_ioc_creation(self):
        """Valid RawIOC should be created successfully."""
        from src.models.enums import IOCType
        from src.models.extraction import RawIOC

        raw_ioc = RawIOC(
            raw_value="192.168.1.1",
            suspected_type=IOCType.IPV4,
            context="Found in malware config",
            line_number=42,
            extraction_confidence=0.95,
        )

        assert raw_ioc.raw_value == "192.168.1.1"
        assert raw_ioc.suspected_type == IOCType.IPV4
        assert raw_ioc.extraction_confidence == 0.95

    def test_context_max_length(self):
        """Context field should reject strings over 500 characters"""
        from pydantic import ValidationError

        from src.models.enums import IOCType
        from src.models.extraction import RawIOC

        with pytest.raises(ValidationError):
            RawIOC(
                raw_value="192.168.1.1",
                suspected_type=IOCType.IPV4,
                context="x" * 501,  # Too long
                extraction_confidence=0.5,
            )

    def test_confidence_must_be_between_0_and_1(self):
        """Extraction confidence must be 0.0 to 1.0."""
        from pydantic import ValidationError

        from src.models.enums import IOCType
        from src.models.extraction import RawIOC

        with pytest.raises(ValidationError):
            RawIOC(
                raw_value="test",
                suspected_type=IOCType.DOMAIN,
                extraction_confidence=1.5,  # Invalid: > 1
            )
