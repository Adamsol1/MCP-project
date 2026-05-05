"""Integration coverage for the analysis + council prototype flow."""

import pytest
from fastapi.testclient import TestClient

from src.api import analysis as analysis_api
from src.api.main import app
from src.models.analysis import AnalysisDraft, CouncilNote, FindingModel, ProcessingResult
from src.services.analysis.analysis_session_store import AnalysisSessionStore

_INTEGRATION_FINDINGS = [
    FindingModel(
        id="F-001",
        title="Credential-access activity",
        finding="Repeated authentication attempts targeted privileged accounts.",
        evidence_summary="Login failures followed by successful access.",
        source="network_telemetry",
        confidence=82,
        relevant_to=["PIR-1"],
        supporting_data={"attack_ids": ["T1078"]},
        why_it_matters="Suggests adversary access development.",
        uncertainties=["Compromised account path unconfirmed."],
    ),
    FindingModel(
        id="F-003",
        title="Phishing staging",
        finding="Lookalike domains appear staged for credential theft.",
        evidence_summary="Passive DNS and hosting overlap support staging.",
        source="osint",
        confidence=76,
        relevant_to=["PIR-2"],
        supporting_data={"domains": ["example-phish.test"]},
        why_it_matters="Supports a parallel intrusion path.",
        uncertainties=["Delivery infrastructure incomplete."],
    ),
]

_INTEGRATION_PROCESSING_RESULT = ProcessingResult(
    findings=_INTEGRATION_FINDINGS,
    gaps=["Attribution remains unresolved.", "Victimology requires confirmation."],
)


class _FakeProcessingResultStore:
    async def get_processing_result(self, session_id: str):  # noqa: ARG002
        return _INTEGRATION_PROCESSING_RESULT


class _FakeAnalysisService:
    async def generate_draft(
        self, processing_result, selected_perspectives=None, _pir=""
    ):
        del selected_perspectives
        return AnalysisDraft(
            summary="Integrated analysis summary.",
            key_judgments=["Integrated judgment."],
            per_perspective_implications={
                "us": ["US implication A", "US implication B"],
                "norway": ["Norway implication A", "Norway implication B"],
                "china": ["China implication A", "China implication B"],
                "eu": ["EU implication A", "EU implication B"],
                "russia": ["Russia implication A", "Russia implication B"],
                "neutral": ["Neutral implication A", "Neutral implication B"],
            },
            recommended_actions=["Integrated action."],
            information_gaps=list(processing_result.gaps),
        )


class _FakeCouncilService:
    async def run_council(
        self,
        session_id,
        debate_point,
        selected_perspectives,
        processing_result,
        analysis_draft,
        finding_ids=None,
        **_kwargs,
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
    monkeypatch.setattr(analysis_api, "AnalysisSessionStore", lambda uow=None: store)
    monkeypatch.setattr(
        analysis_api,
        "AnalysisService",
        lambda _: _FakeAnalysisService(),
    )
    monkeypatch.setattr(analysis_api, "CouncilService", lambda: _FakeCouncilService())
    monkeypatch.setattr(
        analysis_api,
        "ResearchLogger",
        lambda session_id=None: _FakeResearchLogger(session_id=session_id),
    )
    monkeypatch.setattr(
        analysis_api,
        "ProcessingResultStore",
        lambda uow=None: _FakeProcessingResultStore(),
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
    assert (
        reload_payload["latest_council_note"]["summary"]
        == "Integrated council summary."
    )
