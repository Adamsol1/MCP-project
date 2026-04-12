"""Tests for the analysis prototype service."""

import json

import pytest

from src.models.analysis import AnalysisDraft
from src.services import processing_prototype_service as processing_service_module
from src.services.analysis_prototype_service import AnalysisPrototypeService
from src.services.processing_prototype_service import ProcessingPrototypeService

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


def _write_processed_json(tmp_path, session_id: str) -> None:
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "processed.json").write_text(
        json.dumps({"attempts": [json.dumps(VALID_PROCESSING_PAYLOAD)]}),
        encoding="utf-8",
    )


class _FakeLLMService:
    async def generate_json(self, prompt: str) -> dict:
        assert "Processed findings" in prompt
        return {
            "summary": "Gemini-generated assessment of the processed findings.",
            "key_judgments": [
                "Credential-access activity and phishing staging reinforce a coordinated access-development assessment."
            ],
            "per_perspective_implications": {
                "us": ["US implication A", "US implication B"],
                "norway": ["Norway implication A", "Norway implication B"],
                "china": ["China implication A", "China implication B"],
                "eu": ["EU implication A", "EU implication B"],
                "russia": ["Russia implication A", "Russia implication B"],
                "neutral": ["Neutral implication A", "Neutral implication B"],
            },
            "recommended_actions": [
                "Review telecom administrator exposure and related phishing infrastructure."
            ],
            "information_gaps": [
                "Attribution remains unresolved.",
                "Victimology requires confirmation.",
            ],
        }


class TestAnalysisPrototypeService:
    """Test AnalysisPrototypeService."""

    @pytest.mark.asyncio
    async def test_generates_draft_from_valid_processing_result(
        self, monkeypatch, tmp_path
    ):
        """Service should generate a grounded draft from a valid ProcessingResult."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-123")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-123"
        )

        draft = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        joined_judgments = " ".join(draft.key_judgments).lower()

        assert isinstance(draft, AnalysisDraft)
        assert draft.key_judgments
        assert "credential-access" in joined_judgments

    @pytest.mark.asyncio
    async def test_summary_is_non_empty(self, monkeypatch, tmp_path):
        """Generated summary should not be empty."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-456")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-456"
        )

        draft = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        assert draft.summary.strip() != ""

    @pytest.mark.asyncio
    async def test_gaps_propagated_into_information_gaps(self, monkeypatch, tmp_path):
        """Processing gaps should be propagated into the draft."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-789")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-789"
        )

        draft = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        assert draft.information_gaps == processing_result.gaps

    @pytest.mark.asyncio
    async def test_per_perspective_implications_contains_expected_keys(
        self, monkeypatch, tmp_path
    ):
        """Draft should include the canonical perspective keys."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-999")
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-999"
        )

        draft = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        assert set(draft.per_perspective_implications) >= {
            "us",
            "norway",
            "china",
            "eu",
            "russia",
            "neutral",
        }
