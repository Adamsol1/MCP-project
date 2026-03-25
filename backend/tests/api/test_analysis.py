"""Tests for the analysis prototype API."""

from fastapi.testclient import TestClient

from src.api import analysis as analysis_api
from src.api.main import app
from src.models.analysis import AnalysisDraft, CouncilNote
from src.services.analysis_session_store import AnalysisSessionStore


class _FakeAnalysisPrototypeService:
    async def generate_draft(self, processing_result, selected_perspectives=None):
        del selected_perspectives
        return AnalysisDraft(
            summary="Live-style analysis summary grounded in the demo processing result.",
            key_judgments=[
                "Credential access and phishing staging indicate a coordinated access-development pattern."
            ],
            per_perspective_implications={
                "us": ["US implication A", "US implication B"],
                "norway": ["Norway implication A", "Norway implication B"],
                "china": ["China implication A", "China implication B"],
                "eu": ["EU implication A", "EU implication B"],
                "russia": ["Russia implication A", "Russia implication B"],
                "neutral": ["Neutral implication A", "Neutral implication B"],
            },
            recommended_actions=[
                "Validate affected identities and track related infrastructure."
            ],
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
        council_settings=None,
    ):
        assert session_id
        assert processing_result.findings
        assert analysis_draft.summary
        assert len(selected_perspectives) >= 2
        assert finding_ids is None or isinstance(finding_ids, list)
        assert council_settings is None or council_settings.rounds >= 1
        return CouncilNote(
            status="complete",
            question=debate_point or "Assess the selected findings.",
            participants=[
                "US Strategic Analyst",
                "China Strategic Analyst",
                "Neutral Evidence Analyst",
            ],
            rounds_completed=2,
            summary="The council assessed the activity as coordinated access development.",
            key_agreements=[
                "Credential access and phishing staging support a coordinated campaign hypothesis."
            ],
            key_disagreements=[
                "Participants diverged on the likelihood of near-term disruptive intent."
            ],
            final_recommendation="Validate selected findings against victimology and access telemetry before escalating judgments.",
            full_debate=[
                {
                    "round": 1,
                    "participant": "Neutral Evidence Analyst",
                    "response": "The evidence supports a cautious access-development assessment.",
                    "timestamp": "2026-03-20T10:00:00Z",
                }
            ],
            transcript_path="backend/data/outputs/council_transcripts/demo.md",
        )


class _FakeResearchLogger:
    def __init__(self, session_id=None):
        self.session_id = session_id
        self.entries = []

    def create_log(self, entry):
        self.entries.append(entry)


def _configure_analysis_dependencies(monkeypatch, tmp_path):
    store = AnalysisSessionStore(sessions_dir=tmp_path / "sessions")
    logger = _FakeResearchLogger()

    def logger_factory(session_id=None):
        assert session_id is None or isinstance(session_id, str)
        return logger

    monkeypatch.setattr(analysis_api, "AnalysisSessionStore", lambda: store)
    monkeypatch.setattr(
        analysis_api,
        "AnalysisPrototypeService",
        lambda: _FakeAnalysisPrototypeService(),
    )
    monkeypatch.setattr(analysis_api, "CouncilService", lambda: _FakeCouncilService())
    monkeypatch.setattr(analysis_api, "ResearchLogger", logger_factory)

    return store, logger


def test_analysis_draft_happy_path(monkeypatch, tmp_path):
    """POST /api/analysis/draft should return processing, draft, and council slot."""
    _configure_analysis_dependencies(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/analysis/draft",
        json={"session_id": "analysis-session-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "processing_result" in data
    assert "analysis_draft" in data
    assert "latest_council_note" in data
    assert data["latest_council_note"] is None


def test_analysis_draft_requires_session_id(monkeypatch, tmp_path):
    """session_id is required in the request body."""
    _configure_analysis_dependencies(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/analysis/draft",
        json={},
    )

    assert response.status_code == 422


def test_analysis_draft_response_shape_is_valid(monkeypatch, tmp_path):
    """Response should expose a stable, typed shape for frontend use."""
    _configure_analysis_dependencies(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/analysis/draft",
        json={"session_id": "analysis-session-456"},
    )

    assert response.status_code == 200
    data = response.json()

    processing_result = data["processing_result"]
    analysis_draft = data["analysis_draft"]

    assert set(processing_result.keys()) == {"findings", "gaps"}
    assert len(processing_result["findings"]) == 4
    assert len(processing_result["gaps"]) == 4

    assert set(analysis_draft.keys()) == {
        "summary",
        "key_judgments",
        "per_perspective_implications",
        "recommended_actions",
        "information_gaps",
    }
    assert analysis_draft["summary"].strip() != ""
    assert set(analysis_draft["per_perspective_implications"]) >= {
        "us",
        "norway",
        "china",
        "eu",
        "russia",
        "neutral",
    }


def test_analysis_council_happy_path(monkeypatch, tmp_path):
    """Valid council requests should return a structured CouncilNote."""
    _configure_analysis_dependencies(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/analysis/council",
        json={
            "session_id": "analysis-session-council",
            "debate_point": "Assess whether the phishing staging indicates coordinated access development.",
            "finding_ids": ["F-001", "F-002"],
            "selected_perspectives": ["us", "china", "neutral"],
            "council_settings": {
                "mode": "conference",
                "rounds": 3,
                "timeout_seconds": 240,
                "vote_retry_enabled": True,
                "vote_retry_attempts": 2,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["rounds_completed"] == 2
    assert data["participants"] == [
        "US Strategic Analyst",
        "China Strategic Analyst",
        "Neutral Evidence Analyst",
    ]
    assert data["summary"].strip() != ""


def test_analysis_council_requires_two_perspectives(monkeypatch, tmp_path):
    """selected_perspectives must contain at least two items."""
    _configure_analysis_dependencies(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/analysis/council",
        json={
            "session_id": "analysis-session-council",
            "debate_point": "Assess the findings.",
            "selected_perspectives": ["neutral"],
        },
    )

    assert response.status_code == 422


def test_analysis_council_rejects_invalid_finding_ids(monkeypatch, tmp_path):
    """finding_ids must exist in the current processing result."""
    _configure_analysis_dependencies(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/analysis/council",
        json={
            "session_id": "analysis-session-council",
            "debate_point": "Assess the findings.",
            "finding_ids": ["F-999"],
            "selected_perspectives": ["us", "neutral"],
        },
    )

    assert response.status_code == 400
    assert "Unknown finding_ids" in response.json()["detail"]


def test_analysis_council_requires_debate_input(monkeypatch, tmp_path):
    """Council requests need a debate point or selected findings."""
    _configure_analysis_dependencies(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/analysis/council",
        json={
            "session_id": "analysis-session-council",
            "debate_point": "",
            "finding_ids": [],
            "selected_perspectives": ["us", "neutral"],
        },
    )

    assert response.status_code == 422


def test_analysis_council_logs_successful_runs(monkeypatch, tmp_path):
    """Successful council runs should emit an analysis-specific research log entry."""
    _, logger = _configure_analysis_dependencies(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/analysis/council",
        json={
            "session_id": "analysis-session-logging",
            "debate_point": "Assess whether disruption intent is likely.",
            "finding_ids": ["F-004"],
            "selected_perspectives": ["us", "neutral"],
        },
    )

    assert response.status_code == 200
    assert len(logger.entries) == 1
    assert logger.entries[0]["phase"] == "analysis_council"
    assert logger.entries[0]["finding_ids"] == ["F-004"]
    assert logger.entries[0]["council_summary"].strip() != ""
