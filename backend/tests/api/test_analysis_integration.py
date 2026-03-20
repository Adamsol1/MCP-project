"""Integration coverage for the analysis + council prototype flow."""

import pytest
from fastapi.testclient import TestClient

from src.api import analysis as analysis_api
from src.api.main import app
from src.models.analysis import CouncilNote
from src.services.analysis_session_store import AnalysisSessionStore


class _FakeCouncilService:
    async def run_council(
        self,
        session_id,
        debate_point,
        selected_perspectives,
        processing_result,
        analysis_draft,
        finding_ids=None,
    ):
        assert session_id == "integration-session"
        assert len(selected_perspectives) >= 2
        assert processing_result.findings
        assert analysis_draft.summary
        assert finding_ids == ["F-001", "F-003"]
        return CouncilNote(
            status="complete",
            question=debate_point or "Assess the selected findings.",
            participants=[
                "US Strategic Analyst",
                "Neutral Evidence Analyst",
            ],
            rounds_completed=2,
            summary="Integrated council summary.",
            key_agreements=["Agreement A"],
            key_disagreements=["Disagreement A"],
            final_recommendation="Recommendation A",
            full_debate=[
                {
                    "round": 1,
                    "participant": "Neutral Evidence Analyst",
                    "response": "Integrated response.",
                    "timestamp": "2026-03-20T10:00:00Z",
                }
            ],
            transcript_path="backend/data/outputs/council_transcripts/integration.md",
        )


class _FakeResearchLogger:
    def __init__(self, session_id=None):
        self.session_id = session_id

    def create_log(self, entry):  # noqa: ARG002
        return None


@pytest.mark.integration
def test_analysis_and_council_flow_persists_across_reload(monkeypatch, tmp_path):
    """Draft generation, council run, and later reload should reuse persisted state."""
    store = AnalysisSessionStore(sessions_dir=tmp_path / "sessions")
    monkeypatch.setattr(analysis_api, "AnalysisSessionStore", lambda: store)
    monkeypatch.setattr(analysis_api, "CouncilService", lambda: _FakeCouncilService())
    monkeypatch.setattr(
        analysis_api,
        "ResearchLogger",
        lambda session_id=None: _FakeResearchLogger(session_id=session_id),
    )

    client = TestClient(app)

    draft_response = client.post(
        "/api/analysis/draft",
        json={"session_id": "integration-session"},
    )
    assert draft_response.status_code == 200
    draft_payload = draft_response.json()
    assert draft_payload["analysis_draft"]["summary"].strip() != ""
    assert draft_payload["latest_council_note"] is None

    council_response = client.post(
        "/api/analysis/council",
        json={
            "session_id": "integration-session",
            "debate_point": "Assess whether the findings support access development rather than opportunistic activity.",
            "selected_perspectives": ["us", "neutral"],
            "finding_ids": ["F-001", "F-003"],
        },
    )
    assert council_response.status_code == 200
    council_payload = council_response.json()
    assert council_payload["summary"] == "Integrated council summary."

    reload_response = client.post(
        "/api/analysis/draft",
        json={"session_id": "integration-session"},
    )
    assert reload_response.status_code == 200
    reload_payload = reload_response.json()
    assert reload_payload["analysis_draft"] == draft_payload["analysis_draft"]
    assert reload_payload["processing_result"] == draft_payload["processing_result"]
    assert reload_payload["latest_council_note"]["summary"] == "Integrated council summary."
