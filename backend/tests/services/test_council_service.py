"""Tests for the analysis-stage council service."""

from types import SimpleNamespace

import pytest

from src.models.analysis import CouncilNote
from src.services.analysis_prototype_service import AnalysisPrototypeService
from src.services.council_service import CouncilService
from src.services.processing_prototype_service import ProcessingPrototypeService


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
                    response="[ERROR: FileNotFoundError: [WinError 2] The system cannot find the file specified]",
                    timestamp="2026-03-20T10:00:00Z",
                ),
                SimpleNamespace(
                    round=1,
                    participant=request.participants[1].display_name,
                    response="[ERROR: FileNotFoundError: [WinError 2] The system cannot find the file specified]",
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
        assert profile.working_directory == str(tmp_path)
        assert profile.file_tree_injection_enabled is False
        assert profile.decision_graph_enabled is False

    @pytest.mark.asyncio
    async def test_run_council_returns_council_note(self, monkeypatch, tmp_path):
        """Council execution should return a stable CouncilNote."""
        service = CouncilService(working_directory=tmp_path)
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-council"
        )
        analysis_draft = AnalysisPrototypeService().generate_draft(processing_result)

        monkeypatch.setattr(service, "_build_engine", lambda: _FakeEngine())

        result = await service.run_council(
            session_id="session-council",
            debate_point="Assess the strongest interpretation of the selected findings.",
            selected_perspectives=["us", "neutral"],
            processing_result=processing_result,
            analysis_draft=analysis_draft,
            finding_ids=["F-001", "F-002"],
        )

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
        service = CouncilService(working_directory=tmp_path)
        processing_result = ProcessingPrototypeService().get_processing_result(
            "session-council"
        )
        analysis_draft = AnalysisPrototypeService().generate_draft(processing_result)

        monkeypatch.setattr(service, "_build_engine", lambda: _ErrorEngine())

        with pytest.raises(RuntimeError, match="Gemini CLI could not be launched"):
            await service.run_council(
                session_id="session-council",
                debate_point="Assess the strongest interpretation of the selected findings.",
                selected_perspectives=["us", "neutral"],
                processing_result=processing_result,
                analysis_draft=analysis_draft,
                finding_ids=["F-001", "F-002"],
            )
