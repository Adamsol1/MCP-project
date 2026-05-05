"""Tests for persisted analysis session state."""

import json

from src.models.analysis import AnalysisDraft, CouncilNote, ProcessingResult
from src.services.processing import processing_result_store as processing_service_module
from src.services.analysis.analysis_session_store import AnalysisSessionStore
from src.services.processing.processing_result_store import ProcessingResultStore

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


def _make_draft() -> AnalysisDraft:
    return AnalysisDraft(
        summary="Session summary.",
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

    async def test_draft_persistence(self, monkeypatch, tmp_path):
        """Saved drafts should be reloaded after a later read."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-draft")
        store = AnalysisSessionStore(sessions_dir=tmp_path / "analysis-sessions")
        processing_result = await ProcessingResultStore().get_processing_result(
            "session-draft"
        )
        draft = _make_draft()

        await store.save_draft("session-draft", processing_result, draft)
        reloaded = await store.load("session-draft")

        assert reloaded is not None
        assert isinstance(reloaded.processing_result, ProcessingResult)
        assert reloaded.analysis_draft == draft

    async def test_council_note_persistence(self, tmp_path):
        """Saved council notes should remain separate from the persisted draft."""
        store = AnalysisSessionStore(sessions_dir=tmp_path / "analysis-sessions")
        note = _make_note()

        await store.save_council_note("session-council", note)
        reloaded = await store.load("session-council")

        assert reloaded is not None
        assert reloaded.latest_council_note == note
        assert reloaded.analysis_draft is None

    async def test_reload_behavior_preserves_draft_and_latest_note(
        self, monkeypatch, tmp_path
    ):
        """Reloading should preserve both the draft and the latest council note."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-reload")
        store = AnalysisSessionStore(sessions_dir=tmp_path / "analysis-sessions")
        processing_result = await ProcessingResultStore().get_processing_result(
            "session-reload"
        )
        draft = _make_draft()
        note = _make_note()

        await store.save_draft("session-reload", processing_result, draft)
        await store.save_council_note("session-reload", note)

        reloaded = await AnalysisSessionStore(
            sessions_dir=tmp_path / "analysis-sessions"
        ).load("session-reload")

        assert reloaded is not None
        assert reloaded.analysis_draft == draft
        assert reloaded.latest_council_note == note
