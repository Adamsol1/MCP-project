"""Tests for the analysis-stage council service."""

import pytest

from src.models.analysis import AnalysisDraft, CouncilNote, ProcessingResult
from src.services.council_service import CouncilService, get_council_mcp_url

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


class FakeCouncilMCPClient:
    def __init__(self, deliberate_result: dict | None = None):
        self.server_url = "memory://council"
        self.deliberate_result = deliberate_result or {
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
            "transcript_path": "/tmp/council_transcripts/demo.md",
        }

    def connect(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get_prompt(self, name: str, args: dict | None = None):
        if name == "council_behavior":
            return "Use evidence quality as the debate anchor."
        if name == "council_task":
            return f"Task for {args['debate_point']}"
        raise AssertionError(f"Unexpected prompt: {name}")

    async def read_resource(self, uri: str):
        perspective = uri.rsplit("/", 1)[-1]
        return f"{perspective} persona"

    async def call_tool(self, name: str, _args: dict):
        if name == "summarize_entries":
            return []
        if name == "deliberate":
            return self.deliberate_result
        raise AssertionError(f"Unexpected tool: {name}")


def _processing_result() -> ProcessingResult:
    return ProcessingResult.model_validate(VALID_PROCESSING_PAYLOAD)


def _analysis_draft() -> AnalysisDraft:
    return AnalysisDraft(
        summary="Test analysis summary.",
        key_judgments=["Test judgment."],
        per_perspective_implications={"us": [], "neutral": []},
        recommended_actions=["Test action."],
        information_gaps=[],
    )


class TestCouncilService:
    """Test participant construction and runtime defaults."""

    def test_council_url_ignores_local_llm_port(self, monkeypatch):
        monkeypatch.setenv("COUNCIL_MCP_URL", "http://127.0.0.1:8000/sse")

        assert get_council_mcp_url() == "http://127.0.0.1:8003/sse"

    def test_council_url_accepts_explicit_council_port(self, monkeypatch):
        monkeypatch.setenv("COUNCIL_MCP_URL", "http://127.0.0.1:8013/sse")

        assert get_council_mcp_url() == "http://127.0.0.1:8013/sse"

    @pytest.mark.asyncio
    async def test_participant_construction(self):
        """One configured participant should be built per selected perspective."""
        service = CouncilService(mcp_client=FakeCouncilMCPClient())

        participants = await service.build_participants(["us", "neutral", "china"])

        assert [participant["cli"] for participant in participants] == [
            service.DEFAULT_ADAPTER,
            service.DEFAULT_ADAPTER,
            service.DEFAULT_ADAPTER,
        ]
        assert [participant["model"] for participant in participants] == [
            service.DEFAULT_MODEL,
            service.DEFAULT_MODEL,
            service.DEFAULT_MODEL,
        ]
        assert participants[0]["display_name"] == "US Strategic Analyst"
        assert "evidence quality" in participants[1]["persona_prompt"]

    @pytest.mark.asyncio
    async def test_validation_on_too_few_perspectives(self):
        """Fewer than two unique perspectives should fail validation."""
        service = CouncilService(mcp_client=FakeCouncilMCPClient())

        with pytest.raises(ValueError, match="At least 2 perspectives are required"):
            await service.build_participants(["neutral"])

        with pytest.raises(ValueError, match="At least 2 perspectives are required"):
            await service.build_participants(["neutral", "NEUTRAL"])

    def test_runtime_config_defaults(self, tmp_path):
        """Runtime profile should reflect the active app provider defaults."""
        service = CouncilService(
            working_directory=tmp_path,
            mcp_client=FakeCouncilMCPClient(),
        )

        profile = service.runtime_profile

        assert profile.adapter == service.DEFAULT_ADAPTER
        assert profile.model == service.DEFAULT_MODEL
        assert profile.mode == "conference"
        assert profile.rounds == 2
        assert profile.timeout_per_round_seconds == 180
        assert profile.vote_retry_enabled is True
        assert profile.vote_retry_attempts == 1
        assert profile.working_directory == str(tmp_path)
        assert profile.file_tree_injection_enabled is False
        assert profile.decision_graph_enabled is False

    @pytest.mark.asyncio
    async def test_run_council_returns_council_note(self, tmp_path):
        """Council execution should return a stable CouncilNote."""
        service = CouncilService(
            working_directory=tmp_path,
            mcp_client=FakeCouncilMCPClient(),
        )

        result = await service.run_council(
            session_id="session-council",
            debate_point="Assess the strongest interpretation of the selected findings.",
            selected_perspectives=["us", "neutral"],
            processing_result=_processing_result(),
            analysis_draft=_analysis_draft(),
            finding_ids=["F-001", "F-002"],
        )

        assert isinstance(result, CouncilNote)
        assert result.participants == [
            "US Strategic Analyst",
            "Neutral Evidence Analyst",
        ]
        assert result.rounds_completed == 2

    @pytest.mark.asyncio
    async def test_run_council_raises_runtime_error_for_all_error_responses(self, tmp_path):
        """Council execution should fail clearly when all responses are runtime errors."""
        error_result = {
            "status": "complete",
            "participants": ["US Strategic Analyst", "Neutral Evidence Analyst"],
            "rounds_completed": 2,
            "summary": {
                "consensus": "[Summary generation not available]",
                "key_agreements": [],
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
            "transcript_path": "/tmp/council_transcripts/demo.md",
        }
        service = CouncilService(
            working_directory=tmp_path,
            mcp_client=FakeCouncilMCPClient(error_result),
        )

        with pytest.raises(RuntimeError, match="Council runtime failed:"):
            await service.run_council(
                session_id="session-council",
                debate_point="Assess the strongest interpretation.",
                selected_perspectives=["us", "neutral"],
                processing_result=_processing_result(),
                analysis_draft=_analysis_draft(),
                finding_ids=["F-001", "F-002"],
            )
