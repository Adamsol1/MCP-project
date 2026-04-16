"""Tests for the processing prototype service."""

import json

import pytest

from src.models.analysis import ProcessingResult
from src.services import processing_result_store as processing_service_module
from src.services.processing_result_store import (
    PROCESSING_RESULT_UNAVAILABLE_MESSAGE,
    ProcessingResultStore,
)

VALID_PROCESSING_PAYLOAD = {
    "findings": [
        {
            "id": "F-001",
            "title": "Credential-access activity",
            "finding": "Repeated authentication attempts targeted privileged accounts.",
            "evidence_summary": "Login failures were followed by successful access.",
            "source": "network_telemetry",
            "confidence": 82,
            "relevant_to": ["PIR-1"],
            "supporting_data": {"attack_ids": ["T1078"]},
            "why_it_matters": "This suggests adversary access development.",
            "uncertainties": ["The compromised account path is unconfirmed."],
        }
    ],
    "gaps": ["Attribution remains unresolved."],
}

LEGACY_PROCESSING_PAYLOAD = {
    "entities": [
        {
            "id": "E-001",
            "name": "Storebrand privileged access exposure",
            "description": "Privileged access pathways remain exposed through remote administration workflows.",
            "categories": ["infrastructure", "information"],
            "sources": ["manual", "otx"],
            "confidence": 78,
            "relevant_to": ["PIR-1", "PIR-2"],
            "tags": ["access", "storebrand"],
            "first_observed": "2026-04-01",
            "last_updated": "2026-04-10",
        }
    ],
    "gaps": ["Victimology remains incomplete."],
    "processing_summary": "Legacy PMESII summary.",
    "assessment_changed": False,
    "change_summary": None,
}


def _write_processed_json(tmp_path, session_id: str, attempts: list[str]) -> None:
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "processed.json").write_text(
        json.dumps({"attempts": attempts}),
        encoding="utf-8",
    )


class TestProcessingResultStore:
    """Test ProcessingResultStore."""

    def test_successful_load_returns_processing_result(self, monkeypatch, tmp_path):
        """Service should load the session processing result successfully."""
        monkeypatch.setattr(
            processing_service_module,
            "_SESSIONS_DATA_DIR",
            tmp_path,
        )
        _write_processed_json(
            tmp_path,
            "session-123",
            [json.dumps(VALID_PROCESSING_PAYLOAD)],
        )

        result = ProcessingResultStore().get_processing_result("session-123")

        assert isinstance(result, ProcessingResult)
        assert len(result.findings) == 1
        assert len(result.gaps) == 1

    def test_returned_type_is_processing_result(self, monkeypatch, tmp_path):
        """Service should return a validated ProcessingResult instance."""
        monkeypatch.setattr(
            processing_service_module,
            "_SESSIONS_DATA_DIR",
            tmp_path,
        )
        _write_processed_json(
            tmp_path,
            "session-456",
            [json.dumps(VALID_PROCESSING_PAYLOAD)],
        )

        result = ProcessingResultStore().get_processing_result("session-456")

        assert type(result) is ProcessingResult

    def test_prefers_last_valid_attempt(self, monkeypatch, tmp_path):
        """Service should use the most recent valid attempt in processed.json."""
        monkeypatch.setattr(
            processing_service_module,
            "_SESSIONS_DATA_DIR",
            tmp_path,
        )
        older_payload = {
            **VALID_PROCESSING_PAYLOAD,
            "findings": [{**VALID_PROCESSING_PAYLOAD["findings"][0], "id": "F-OLD"}],
        }
        newer_payload = {
            **VALID_PROCESSING_PAYLOAD,
            "findings": [{**VALID_PROCESSING_PAYLOAD["findings"][0], "id": "F-NEW"}],
        }
        _write_processed_json(
            tmp_path,
            "session-789",
            [
                json.dumps(older_payload),
                f"```json\n{json.dumps(newer_payload)}\n```",
            ],
        )

        result = ProcessingResultStore().get_processing_result("session-789")

        assert result.findings[0].id == "F-NEW"

    def test_converts_legacy_entities_schema(self, monkeypatch, tmp_path):
        """Service should convert older PMESII processing output into analysis findings."""
        monkeypatch.setattr(
            processing_service_module,
            "_SESSIONS_DATA_DIR",
            tmp_path,
        )
        _write_processed_json(
            tmp_path,
            "legacy-session",
            [json.dumps(LEGACY_PROCESSING_PAYLOAD)],
        )

        result = ProcessingResultStore().get_processing_result("legacy-session")

        assert len(result.findings) == 1
        assert result.findings[0].id == "E-001"
        assert result.findings[0].title == "Storebrand privileged access exposure"
        assert result.findings[0].source == "manual"
        assert result.gaps == ["Victimology remains incomplete."]

    def test_missing_file_raises_clear_error(self, monkeypatch, tmp_path):
        """Missing processed.json should raise the processing-required error."""
        monkeypatch.setattr(
            processing_service_module,
            "_SESSIONS_DATA_DIR",
            tmp_path,
        )

        with pytest.raises(ValueError, match=PROCESSING_RESULT_UNAVAILABLE_MESSAGE):
            ProcessingResultStore().get_processing_result("nonexistent-session")

    def test_invalid_file_raises_clear_error(self, monkeypatch, tmp_path):
        """Invalid JSON should raise the processing-required error."""
        monkeypatch.setattr(
            processing_service_module,
            "_SESSIONS_DATA_DIR",
            tmp_path,
        )
        session_dir = tmp_path / "invalid-session"
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "processed.json").write_text("{not-valid-json", encoding="utf-8")

        with pytest.raises(ValueError, match=PROCESSING_RESULT_UNAVAILABLE_MESSAGE):
            ProcessingResultStore().get_processing_result("invalid-session")

    def test_invalid_payload_raises_clear_error(self, monkeypatch, tmp_path):
        """Schema-invalid payload should raise the processing-required error."""
        monkeypatch.setattr(
            processing_service_module,
            "_SESSIONS_DATA_DIR",
            tmp_path,
        )
        _write_processed_json(
            tmp_path,
            "invalid-payload-session",
            [json.dumps({"findings": [{"confidence": 999}], "gaps": []})],
        )

        with pytest.raises(ValueError, match=PROCESSING_RESULT_UNAVAILABLE_MESSAGE):
            ProcessingResultStore().get_processing_result(
                "invalid-payload-session"
            )
