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


class TestExtractedContent:
    """Test ExtractedContent model."""

    def test_valid_extracted_content_creation(self):
        """Valid ExtractedContent should be created successfully."""
        from datetime import datetime

        from src.models.enums import ExtractionMethod, IOCType
        from src.models.extraction import ExtractedContent, RawIOC

        raw_ioc = RawIOC(
            raw_value="192.168.1.1",
            suspected_type=IOCType.IPV4,
            extraction_confidence=0.9,
        )

        content = ExtractedContent(
            file_upload_id="upload-123",
            extracted_at=datetime.now(),
            extraction_method=ExtractionMethod.REGEX,
            raw_iocs=[raw_ioc],
        )

        assert content.file_upload_id == "upload-123"
        assert len(content.raw_iocs) == 1

    def test_extracted_content_with_optional_fields(self):
        """ExtractedContent should accept optional fields."""
        from datetime import datetime

        from src.models.enums import ExtractionMethod
        from src.models.extraction import ExtractedContent

        content = ExtractedContent(
            file_upload_id="upload-456",
            extracted_at=datetime.now(),
            extraction_method=ExtractionMethod.AI_EXTRACTION,
            raw_iocs=[],
            raw_text="Some extracted text for AI processing",
            detected_schema={"type": "otx_pulse"},
            source_metadata={"version": "1.0"},
            extraction_errors=["Warning: some content skipped"],
        )

        assert content.raw_text == "Some extracted text for AI processing"
        assert content.detected_schema == {"type": "otx_pulse"}


class TestPDFExtractedContent:
    """Test PDFExtractedContent model for PDF-specific extraction."""

    def test_pdf_extracted_content_creation(self):
        """PDFExtractedContent should include PDF-specific fields."""
        from datetime import datetime

        from src.models.enums import ExtractionMethod
        from src.models.extraction import PDFExtractedContent

        pdf_content = PDFExtractedContent(
            file_upload_id="pdf-upload-123",
            extracted_at=datetime.now(),
            extraction_method=ExtractionMethod.AI_EXTRACTION,
            raw_iocs=[],
            page_count=10,
            ocr_applied=True,
            document_title="Threat Analysis Report",
            document_author="Security Team",
        )

        assert pdf_content.page_count == 10
        assert pdf_content.ocr_applied is True
        assert pdf_content.document_title == "Threat Analysis Report"

    def test_pdf_inherits_from_extracted_content(self):
        """PDFExtractedContent should have all ExtractedContent fields."""
        from src.models.extraction import ExtractedContent, PDFExtractedContent

        # Verify inheritance
        assert issubclass(PDFExtractedContent, ExtractedContent)
