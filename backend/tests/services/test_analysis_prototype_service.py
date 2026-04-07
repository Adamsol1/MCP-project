"""Tests for the analysis prototype service."""

import pytest

from src.models.analysis import AnalysisDraft
from src.services.analysis_prototype_service import AnalysisPrototypeService
from src.services.processing_prototype_service import ProcessingPrototypeService


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
    async def test_generates_draft_from_valid_processing_result(self):
        """Service should generate a grounded draft from a valid ProcessingResult."""
        processing_result, _ = ProcessingPrototypeService().get_processing_result(
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
    async def test_summary_is_non_empty(self):
        """Generated summary should not be empty."""
        processing_result, _ = ProcessingPrototypeService().get_processing_result(
            "session-456"
        )

        draft = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        assert draft.summary.strip() != ""

    @pytest.mark.asyncio
    async def test_gaps_propagated_into_information_gaps(self):
        """Processing gaps should be propagated into the draft."""
        processing_result, _ = ProcessingPrototypeService().get_processing_result(
            "session-789"
        )

        draft = await AnalysisPrototypeService(
            llm_service=_FakeLLMService()
        ).generate_draft(processing_result)

        assert draft.information_gaps == processing_result.gaps

    @pytest.mark.asyncio
    async def test_per_perspective_implications_contains_expected_keys(self):
        """Draft should include the canonical perspective keys."""
        processing_result, _ = ProcessingPrototypeService().get_processing_result(
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
