"""Tests for the analysis prototype service."""

from src.models.analysis import AnalysisDraft
from src.services.analysis_prototype_service import AnalysisPrototypeService
from src.services.processing_prototype_service import ProcessingPrototypeService


class TestAnalysisPrototypeService:
    """Test AnalysisPrototypeService."""

    def test_generates_draft_from_valid_processing_result(self):
        """Service should generate a grounded draft from a valid ProcessingResult."""
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-123"
        )

        draft = AnalysisPrototypeService().generate_draft(processing_result)

        joined_judgments = " ".join(draft.key_judgments).lower()

        assert isinstance(draft, AnalysisDraft)
        assert draft.key_judgments
        assert "credential-access" in joined_judgments

    def test_summary_is_non_empty(self):
        """Generated summary should not be empty."""
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-456"
        )

        draft = AnalysisPrototypeService().generate_draft(processing_result)

        assert draft.summary.strip() != ""

    def test_gaps_propagated_into_information_gaps(self):
        """Processing gaps should be propagated into the draft."""
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-789"
        )

        draft = AnalysisPrototypeService().generate_draft(processing_result)

        assert draft.information_gaps == processing_result.gaps

    def test_per_perspective_implications_contains_expected_keys(self):
        """Draft should include the canonical perspective keys."""
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-999"
        )

        draft = AnalysisPrototypeService().generate_draft(processing_result)

        assert set(draft.per_perspective_implications) >= {
            "us",
            "norway",
            "china",
            "eu",
            "russia",
            "neutral",
        }
