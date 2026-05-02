"""Tests for the analysis-stage council service."""

import json
from contextlib import asynccontextmanager

import pytest

from src.models.analysis import AnalysisDraft
from src.services.processing import processing_result_store as processing_service_module
from src.services.council.council_service import CouncilService
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
        },
        {
            "id": "F-002",
            "title": "Phishing staging",
            "finding": "Lookalike domains appear staged for credential theft.",
            "evidence_summary": "Passive DNS and hosting overlap support staging.",
            "source": "osint",
            "confidence": 76,
            "relevant_to": ["PIR-2"],
            "supporting_data": {"domains": ["example-phish.test"]},
            "why_it_matters": "This supports a parallel intrusion path.",
            "uncertainties": ["Delivery infrastructure remains incomplete."],
        },
    ],
    "gaps": [
        "Attribution remains unresolved.",
        "Victimology requires confirmation.",
    ],
}

_FAKE_DELIBERATE_RESULT = {
    "status": "complete",
    "participants": ["US Strategic Analyst", "Neutral Evidence Analyst"],
    "rounds_completed": 2,
    "summary": {
        "consensus": "Consensus summary.",
        "key_agreements": ["Agreement A"],
        "key_disagreements": ["Disagreement A"],
        "final_recommendation": "Recommendation A",
    },
    "full_debate": [
        {
            "round": 1,
            "participant": "US Strategic Analyst",
            "response": "Response A",
            "timestamp": "2026-03-20T10:00:00Z",
        }
    ],
    "transcript_path": "/mock/council_transcripts/demo.md",
}

_ERROR_DELIBERATE_RESULT = {
    "status": "complete",
    "participants": ["US Strategic Analyst", "Neutral Evidence Analyst"],
    "rounds_completed": 2,
    "summary": {
        "consensus": "[Summary generation not available]",
        "key_agreements": ["No AI summary available"],
        "key_disagreements": [],
        "final_recommendation": "Please review the full debate below.",
    },
    "full_debate": [
        {
            "round": 1,
            "participant": "US Strategic Analyst",
            "response": "[ERROR: RuntimeError: synthetic backend failure]",
            "timestamp": "2026-03-20T10:00:00Z",
        },
        {
            "round": 1,
            "participant": "Neutral Evidence Analyst",
            "response": "[ERROR: RuntimeError: synthetic backend failure]",
            "timestamp": "2026-03-20T10:00:00Z",
        },
    ],
    "transcript_path": "/mock/council_transcripts/demo.md",
}


class _FakeMCPClient:
    """Minimal MCP client stub for council service tests."""

    def __init__(self, deliberate_result: dict):
        self._deliberate_result = deliberate_result
        self.server_url = "http://mock-council/"

    @asynccontextmanager
    async def connect(self):
        yield self

    async def get_prompt(self, name, params=None):
        perspective = (params or {}).get("perspective", "")
        if name == "persona" and perspective == "neutral":
            return "You are a neutral analyst focused on evidence quality and logical consistency."
        return f"mock-{name}-prompt"

    async def call_tool(self, name, params=None):
        if name == "deliberate":
            return self._deliberate_result
        return []


def _write_processed_json(tmp_path, session_id: str) -> None:
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "processed.json").write_text(
        json.dumps({"attempts": [json.dumps(VALID_PROCESSING_PAYLOAD)]}),
        encoding="utf-8",
    )


class TestCouncilService:
    """Test participant construction and runtime defaults."""

    async def test_participant_construction(self, monkeypatch):
        """One gemini participant should be built per selected perspective."""
        service = CouncilService()

        async def fake_get_prompt(name, params=None):
            perspective = (params or {}).get("perspective", "")
            if name == "persona" and perspective == "neutral":
                return "You are a neutral analyst focused on evidence quality and logical consistency."
            return f"mock-{name}-prompt"

        monkeypatch.setattr(service.mcp_client, "get_prompt", fake_get_prompt)

        participants = await service.build_participants(["us", "neutral", "china"])

        assert [p["cli"] for p in participants] == ["gemini", "gemini", "gemini"]
        assert [p["model"] for p in participants] == [
            "gemini-2.5-flash",
            "gemini-2.5-flash",
            "gemini-2.5-flash",
        ]
        assert participants[0]["display_name"] == "US Strategic Analyst"
        assert "evidence quality" in participants[1]["persona_prompt"]

    async def test_validation_on_too_few_perspectives(self, monkeypatch):
        """Fewer than two unique perspectives should fail validation."""
        service = CouncilService()

        async def fake_get_prompt(name, params=None):
            return f"mock-{name}-prompt"

        monkeypatch.setattr(service.mcp_client, "get_prompt", fake_get_prompt)

        with pytest.raises(ValueError, match="At least 2 perspectives are required"):
            await service.build_participants(["neutral"])

        with pytest.raises(ValueError, match="At least 2 perspectives are required"):
            await service.build_participants(["neutral", "NEUTRAL"])

    def test_runtime_config_defaults(self, tmp_path):
        """Runtime profile should reflect the app council defaults."""
        service = CouncilService(working_directory=tmp_path)

        profile = service.runtime_profile

        assert profile.adapter == "gemini"
        assert profile.model == "gemini-2.5-flash"
        assert profile.mode == "conference"
        assert profile.rounds == 2
        assert profile.timeout_per_round_seconds == 180
        assert profile.vote_retry_enabled is True
        assert profile.vote_retry_attempts == 1
        assert profile.working_directory == str(tmp_path)
        assert profile.file_tree_injection_enabled is False
        assert profile.decision_graph_enabled is False

    @pytest.mark.asyncio
    async def test_run_council_returns_council_note(self, monkeypatch, tmp_path):
        """Council execution should return a stable CouncilNote."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-council")

        processing_result = await ProcessingResultStore().get_processing_result(
            "session-council"
        )
        analysis_draft = AnalysisDraft(
            summary="Test analysis summary.",
            key_judgments=["Test judgment."],
            per_perspective_implications={"us": [], "neutral": []},
            recommended_actions=["Test action."],
            information_gaps=[],
        )

        service = CouncilService(
            mcp_client=_FakeMCPClient(_FAKE_DELIBERATE_RESULT),
            working_directory=tmp_path,
        )

        result = await service.run_council(
            session_id="session-council",
            debate_point="Assess the strongest interpretation of the selected findings.",
            selected_perspectives=["us", "neutral"],
            processing_result=processing_result,
            analysis_draft=analysis_draft,
            finding_ids=["F-001", "F-002"],
        )

        from src.models.analysis import CouncilNote

        assert isinstance(result, CouncilNote)
        assert result.participants == [
            "US Strategic Analyst",
            "Neutral Evidence Analyst",
        ]
        assert result.rounds_completed == 2

    @pytest.mark.asyncio
    async def test_run_council_raises_runtime_error_for_all_error_responses(
        self, monkeypatch, tmp_path
    ):
        """Council execution should fail clearly when all participant responses are runtime errors."""
        monkeypatch.setattr(processing_service_module, "_SESSIONS_DATA_DIR", tmp_path)
        _write_processed_json(tmp_path, "session-council")

        processing_result = await ProcessingResultStore().get_processing_result(
            "session-council"
        )
        analysis_draft = AnalysisDraft(
            summary="Test analysis summary.",
            key_judgments=["Test judgment."],
            per_perspective_implications={"us": [], "neutral": []},
            recommended_actions=["Test action."],
            information_gaps=[],
        )

        service = CouncilService(
            mcp_client=_FakeMCPClient(_ERROR_DELIBERATE_RESULT),
            working_directory=tmp_path,
        )

        with pytest.raises(RuntimeError, match="Council runtime failed:"):
            await service.run_council(
                session_id="session-council",
                debate_point="Assess the strongest interpretation of the selected findings.",
                selected_perspectives=["us", "neutral"],
                processing_result=processing_result,
                analysis_draft=analysis_draft,
                finding_ids=["F-001", "F-002"],
            )
