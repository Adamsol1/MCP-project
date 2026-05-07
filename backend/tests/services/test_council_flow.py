import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models.analysis import AnalysisDraft, CouncilNote, FindingModel, ProcessingResult
from src.models.dialogue import DialogueAction
from src.services.state_machines.council_flow import CouncilFlow, CouncilState


def _make_analysis_result():
    processing = ProcessingResult(
        findings=[
            FindingModel(
                id="f1",
                title="Finding",
                finding="Detailed finding statement",
                evidence_summary="Evidence summary",
                why_it_matters="Matters",
                confidence=70,
                source="open_source",
                supporting_data={},
            )
        ],
        gaps=[],
    )
    draft = AnalysisDraft(
        title="Draft",
        summary="Summary",
        key_judgments=[],
        per_perspective_implications={},
        recommended_actions=[],
        information_gaps=[],
    )
    return {
        "processing_result": processing.model_dump(),
        "analysis_draft": draft.model_dump(),
    }


def _make_council_note():
    return CouncilNote(
        status="complete",
        question="Is this a threat?",
        participants=["Neutral Evidence Analyst"],
        rounds_completed=1,
        summary="Test consensus reached",
        key_agreements=["Agreement"],
        key_disagreements=[],
        final_recommendation="Recommended action",
        full_debate=[],
    )


class TestSerialization:
    def test_to_dict_contains_session_and_state(self):
        # arrange
        flow = CouncilFlow(session_id="sess-1")

        # act
        data = flow.to_dict()

        # assert
        assert data["session_id"] == "sess-1"
        assert data["state"] == "idle"
        assert data["latest_council_note"] is None

    def test_from_dict_restores_complete_state(self):
        # arrange
        data = {
            "session_id": "sess-1",
            "state": "complete",
            "latest_council_note": {"debate_point": "Test"},
        }

        # act
        flow = CouncilFlow.from_dict(data)

        # assert
        assert flow.state == CouncilState.COMPLETE
        assert flow.latest_council_note == {"debate_point": "Test"}

    def test_from_dict_handles_missing_council_note(self):
        # arrange
        data = {"session_id": "sess-1", "state": "idle"}

        # act
        flow = CouncilFlow.from_dict(data)

        # assert
        assert flow.latest_council_note is None


class TestProcessUserMessage:
    @pytest.mark.asyncio
    async def test_returns_error_when_analysis_flow_is_none(self):
        # arrange
        flow = CouncilFlow(session_id="sess-1")

        # act
        response = await flow.process_user_message(
            debate_point="Is this a threat?",
            finding_ids=[],
            selected_perspectives=["neutral"],
            council_service=MagicMock(),
            analysis_flow=None,
        )

        # assert
        assert response.action == DialogueAction.ERROR

    @pytest.mark.asyncio
    async def test_returns_error_when_analysis_result_is_none(self):
        # arrange
        flow = CouncilFlow(session_id="sess-1")
        mock_analysis_flow = MagicMock()
        mock_analysis_flow.analysis_result = None

        # act
        response = await flow.process_user_message(
            debate_point="Test",
            finding_ids=[],
            selected_perspectives=["neutral"],
            council_service=MagicMock(),
            analysis_flow=mock_analysis_flow,
        )

        # assert
        assert response.action == DialogueAction.ERROR

    @pytest.mark.asyncio
    async def test_runs_council_and_returns_show_council_action(self):
        # arrange
        flow = CouncilFlow(session_id="sess-1")
        mock_analysis_flow = MagicMock()
        mock_analysis_flow.analysis_result = _make_analysis_result()
        mock_council_service = MagicMock()
        mock_council_service.run_council = AsyncMock(return_value=_make_council_note())

        # act
        response = await flow.process_user_message(
            debate_point="Is this a threat?",
            finding_ids=["f1"],
            selected_perspectives=["neutral"],
            council_service=mock_council_service,
            analysis_flow=mock_analysis_flow,
        )

        # assert
        assert response.action == DialogueAction.SHOW_COUNCIL
        assert flow.state == CouncilState.COMPLETE

    @pytest.mark.asyncio
    async def test_stores_council_note_on_success(self):
        # arrange
        flow = CouncilFlow(session_id="sess-1")
        mock_analysis_flow = MagicMock()
        mock_analysis_flow.analysis_result = _make_analysis_result()
        mock_council_service = MagicMock()
        mock_council_service.run_council = AsyncMock(return_value=_make_council_note())

        # act
        await flow.process_user_message(
            debate_point="Test",
            finding_ids=[],
            selected_perspectives=["neutral"],
            council_service=mock_council_service,
            analysis_flow=mock_analysis_flow,
        )

        # assert
        assert flow.latest_council_note is not None
        assert flow.latest_council_note["question"] == "Is this a threat?"

    @pytest.mark.asyncio
    async def test_returns_error_when_council_service_raises(self):
        # arrange
        flow = CouncilFlow(session_id="sess-1")
        mock_analysis_flow = MagicMock()
        mock_analysis_flow.analysis_result = _make_analysis_result()
        mock_council_service = MagicMock()
        mock_council_service.run_council = AsyncMock(side_effect=Exception("Council failed"))

        # act
        response = await flow.process_user_message(
            debate_point="Test",
            finding_ids=[],
            selected_perspectives=["neutral"],
            council_service=mock_council_service,
            analysis_flow=mock_analysis_flow,
        )

        # assert
        assert response.action == DialogueAction.ERROR
