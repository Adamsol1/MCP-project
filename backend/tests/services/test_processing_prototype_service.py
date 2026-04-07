"""Tests for the processing prototype service."""

import json

import pytest

from src.models.analysis import ProcessingResult
from src.services.processing_prototype_service import ProcessingPrototypeService


class TestProcessingPrototypeService:
    """Test ProcessingPrototypeService."""

    def test_successful_load_returns_processing_result(self):
        """Service should load the demo processing result successfully."""
        service = ProcessingPrototypeService()

        result = service.get_processing_result("session-123")

        assert isinstance(result, ProcessingResult)
        assert len(result.findings) == 4
        assert len(result.gaps) == 4

    def test_returned_type_is_processing_result(self):
        """Service should return a validated ProcessingResult instance."""
        service = ProcessingPrototypeService()

        result = service.get_processing_result("session-456")

        assert type(result) is ProcessingResult

    def test_named_dataset_loads_alternate_demo_payload(self):
        """Service should load alternate demo payloads by dataset name."""
        service = ProcessingPrototypeService(dataset_name="demo_processing_result_3")

        result = service.get_processing_result("session-456")

        assert type(result) is ProcessingResult
        assert len(result.findings) == 6
        assert len(result.gaps) == 6

    def test_unknown_dataset_raises_clear_error(self):
        """Unknown dataset names should fail before any file access."""
        with pytest.raises(ValueError, match="Unknown demo dataset"):
            ProcessingPrototypeService(dataset_name="not_a_real_demo")

    def test_missing_file_raises_clear_error(self, tmp_path):
        """Missing prototype file should raise a clear backend error."""
        missing_path = tmp_path / "missing_processing_result.json"
        service = ProcessingPrototypeService(prototype_path=missing_path)

        with pytest.raises(ValueError, match="Failed to load processing result"):
            service.get_processing_result("session-789")

    def test_invalid_file_raises_clear_error(self, tmp_path):
        """Invalid JSON should raise a clear backend error."""
        invalid_path = tmp_path / "invalid_processing_result.json"
        invalid_path.write_text("{not-valid-json", encoding="utf-8")
        service = ProcessingPrototypeService(prototype_path=invalid_path)

        with pytest.raises(
            ValueError, match="Failed to parse processing result JSON"
        ):
            service.get_processing_result("session-789")

    def test_invalid_payload_raises_clear_error(self, tmp_path):
        """Schema-invalid payload should raise a clear backend error."""
        invalid_payload_path = tmp_path / "invalid_payload.json"
        invalid_payload_path.write_text(
            json.dumps({"findings": [{"confidence": 999}], "gaps": []}),
            encoding="utf-8",
        )
        service = ProcessingPrototypeService(prototype_path=invalid_payload_path)

        with pytest.raises(ValueError, match="Failed to validate processing result"):
            service.get_processing_result("session-789")
