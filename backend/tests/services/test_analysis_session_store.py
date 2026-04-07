"""Tests for persisted analysis session state."""

from src.models.analysis import AnalysisDraft, CouncilNote, ProcessingResult
from src.services.analysis_session_store import AnalysisSessionStore
from src.services.processing_prototype_service import ProcessingPrototypeService


def _make_draft() -> AnalysisDraft:
    return AnalysisDraft(
        summary="Demo summary.",
        key_judgments=["Judgment A"],
        per_perspective_implications={"neutral": ["Implication A"]},
        recommended_actions=["Action A"],
        information_gaps=["Gap A"],
    )


def _make_note() -> CouncilNote:
    return CouncilNote(
        status="complete",
        question="Assess the findings.",
        participants=["Neutral Evidence Analyst", "US Strategic Analyst"],
        rounds_completed=2,
        summary="Council summary.",
        key_agreements=["Agreement A"],
        key_disagreements=["Disagreement A"],
        final_recommendation="Recommendation A",
        full_debate=[
            {
                "round": 1,
                "participant": "Neutral Evidence Analyst",
                "response": "Response A",
                "timestamp": "2026-03-20T10:00:00Z",
            }
        ],
        transcript_path=None,
    )


class TestAnalysisSessionStore:
    """Test persisted analysis draft and council state."""

    def test_draft_persistence(self, tmp_path):
        """Saved drafts should be reloaded after a later read."""
        store = AnalysisSessionStore(sessions_dir=tmp_path)
        processing_result, _ = ProcessingPrototypeService().get_processing_result(
            "session-draft"
        )
        draft = _make_draft()

        store.save_draft("session-draft", processing_result, draft)
        reloaded = store.load("session-draft")

        assert reloaded is not None
        assert isinstance(reloaded.processing_result, ProcessingResult)
        assert reloaded.analysis_draft == draft

    def test_council_note_persistence(self, tmp_path):
        """Saved council notes should remain separate from the persisted draft."""
        store = AnalysisSessionStore(sessions_dir=tmp_path)
        note = _make_note()

        store.save_council_note("session-council", note)
        reloaded = store.load("session-council")

        assert reloaded is not None
        assert reloaded.latest_council_note == note
        assert reloaded.analysis_draft is None

    def test_reload_behavior_preserves_draft_and_latest_note(self, tmp_path):
        """Reloading should preserve both the draft and the latest council note."""
        store = AnalysisSessionStore(sessions_dir=tmp_path)
        processing_result, _ = ProcessingPrototypeService().get_processing_result(
            "session-reload"
        )
        draft = _make_draft()
        note = _make_note()

        store.save_draft("session-reload", processing_result, draft)
        store.save_council_note("session-reload", note)

        reloaded = AnalysisSessionStore(sessions_dir=tmp_path).load("session-reload")

        assert reloaded is not None
        assert reloaded.analysis_draft == draft
        assert reloaded.latest_council_note == note
