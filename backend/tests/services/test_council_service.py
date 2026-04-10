"""Tests for the analysis-stage council service."""

import json
from types import SimpleNamespace

import pytest

from src.services import processing_prototype_service as processing_service_module
from src.services.analysis_prototype_service import AnalysisPrototypeService
from src.services.council_service import CouncilService
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


def _write_processed_json(tmp_path, session_id: str) -> None:
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "processed.json").write_text(
        json.dumps({"attempts": [json.dumps(VALID_PROCESSING_PAYLOAD)]}),
        encoding="utf-8",
    )


class _FakeEngine:
    async def execute(self, request):
        return SimpleNamespace(
            status="complete",
            participants=[p.display_name or p.model for p in request.participants],
            rounds_completed=request.rounds,
            summary=SimpleNamespace(
                consensus="Consensus summary.",
                key_agreements=["Agreement A"],
                key_disagreements=["Disagreement A"],
                final_recommendation="Recommendation A",
            ),
            full_debate=[
                SimpleNamespace(
                    round=1,
                    participant=request.participants[0].display_name,
                    response="Response A",
                    timestamp="2026-03-20T10:00:00Z",
                )
            ],
            transcript_path=str(
                request.working_directory + "/council_transcripts/demo.md"
            ),
        )


class _ErrorEngine:
    async def execute(self, request):
        return SimpleNamespace(
            status="complete",
            participants=[p.display_name or p.model for p in request.participants],
            rounds_completed=request.rounds,
            summary=SimpleNamespace(
                consensus="[Summary generation not available]",
                key_agreements=["No AI summary available"],
                key_disagreements=[],
                final_recommendation="Please review the full debate below.",
            ),
            full_debate=[
                SimpleNamespace(
                    round=1,
                    participant=request.participants[0].display_name,
                    response="[ERROR: RuntimeError: synthetic backend failure]",
                    timestamp="2026-03-20T10:00:00Z",
                ),
                SimpleNamespace(
                    round=1,
                    participant=request.participants[1].display_name,
                    response="[ERROR: RuntimeError: synthetic backend failure]",
                    timestamp="2026-03-20T10:00:00Z",
                ),
            ],
            transcript_path=str(
                request.working_directory + "/council_transcripts/demo.md"
            ),
        )


class TestCouncilService:
    """Test participant construction and runtime defaults."""

    def test_participant_construction(self):
        """One gemini participant should be built per selected perspective."""
        service = CouncilService()

        participants = service.build_participants(["us", "neutral", "china"])

        assert [participant.cli for participant in participants] == [
            "gemini",
            "gemini",
            "gemini",
        ]
        assert [participant.model for participant in participants] == [
            "gemini-2.5-flash",
            "gemini-2.5-flash",
            "gemini-2.5-flash",
        ]
        assert participants[0].display_name == "US Strategic Analyst"
        assert "evidence quality" in participants[1].persona_prompt

    def test_validation_on_too_few_perspectives(self):
        """Fewer than two unique perspectives should fail validation."""
        service = CouncilService()

        with pytest.raises(
            ValueError, match="At least 2 perspectives are required"
        ):
            service.build_participants(["neutral"])

        with pytest.raises(
            ValueError, match="At least 2 perspectives are required"
        ):
            service.build_participants(["neutral", "NEUTRAL"])

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
        service = CouncilService(working_directory=tmp_path)
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-council"
        )
        analysis_draft = await AnalysisPrototypeService().generate_draft(
            processing_result
        )

        monkeypatch.setattr(service, "_build_engine", lambda profile: _FakeEngine())

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
        service = CouncilService(working_directory=tmp_path)
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-council"
        )
        analysis_draft = await AnalysisPrototypeService().generate_draft(
            processing_result
        )

        monkeypatch.setattr(service, "_build_engine", lambda profile: _ErrorEngine())

        with pytest.raises(RuntimeError, match="Council runtime failed:"):
            await service.run_council(
                session_id="session-council",
                debate_point="Assess the strongest interpretation of the selected findings.",
                selected_perspectives=["us", "neutral"],
                processing_result=processing_result,
                analysis_draft=analysis_draft,
                finding_ids=["F-001", "F-002"],
            )
