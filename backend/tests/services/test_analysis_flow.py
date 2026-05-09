import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models.analysis import AnalysisDraft, FindingModel, ProcessingResult
from src.models.confidence import PerspectiveAssertion
from src.models.dialogue import DialogueAction
from src.services.state_machines.analysis_flow import AnalysisFlow, AnalysisState


def _make_finding():
    return FindingModel(
        id="f1",
        title="Test Finding",
        finding="Detailed finding statement",
        evidence_summary="Evidence summary",
        why_it_matters="Matters",
        confidence=70,
        source="open_source",
        supporting_data={},
    )


def _make_processing_result():
    return ProcessingResult(findings=[_make_finding()], gaps=["Gap 1"])


def _make_analysis_draft():
    return AnalysisDraft(
        title="Test Draft",
        summary="Test summary",
        key_judgments=["Key judgment"],
        per_perspective_implications={},
        recommended_actions=["Action"],
        information_gaps=[],
    )


class TestSerialization:
    def test_to_dict_contains_session_and_state(self):
        # arrange
        flow = AnalysisFlow(session_id="sess-1", pir="test pir")

        # act
        data = flow.to_dict()

        # assert
        assert data["session_id"] == "sess-1"
        assert data["state"] == "pending"
        assert data["pir"] == "test pir"

    def test_from_dict_restores_complete_state(self):
        # arrange
        data = {
            "session_id": "sess-1",
            "state": "complete",
            "pir": "pir data",
            "analysis_result": {"some": "result"},
        }

        # act
        flow = AnalysisFlow.from_dict(data)

        # assert
        assert flow.session_id == "sess-1"
        assert flow.state == AnalysisState.COMPLETE
        assert flow.analysis_result == {"some": "result"}

    def test_from_dict_handles_missing_analysis_result(self):
        # arrange
        data = {"session_id": "sess-1", "state": "pending", "pir": ""}

        # act
        flow = AnalysisFlow.from_dict(data)

        # assert
        assert flow.analysis_result is None


class TestExtractPirs:
    def test_returns_empty_when_pir_is_empty_string(self):
        # arrange
        flow = AnalysisFlow(pir="")

        # act
        result = flow._extract_pirs()

        # assert
        assert result == []

    def test_returns_empty_on_invalid_json(self):
        # arrange
        flow = AnalysisFlow(pir="not valid json")

        # act
        result = flow._extract_pirs()

        # assert
        assert result == []

    def test_returns_pir_list_from_valid_json(self):
        # arrange
        pir_data = {"pirs": [{"question": "What is the threat?", "id": "p1"}]}
        flow = AnalysisFlow(pir=json.dumps(pir_data))

        # act
        result = flow._extract_pirs()

        # assert
        assert len(result) == 1
        assert result[0]["question"] == "What is the threat?"

    def test_filters_out_pirs_without_question_field(self):
        # arrange
        pir_data = {"pirs": [{"id": "p1"}, {"question": "Valid?", "id": "p2"}]}
        flow = AnalysisFlow(pir=json.dumps(pir_data))

        # act
        result = flow._extract_pirs()

        # assert
        assert len(result) == 1
        assert result[0]["id"] == "p2"


class TestInitialize:
    @pytest.mark.asyncio
    async def test_returns_error_when_session_id_is_none(self):
        # arrange
        flow = AnalysisFlow(session_id=None)

        # act
        response = await flow.initialize(
            processing_service=MagicMock(),
            analysis_service=MagicMock(),
        )

        # assert
        assert response.action == DialogueAction.ERROR

    @pytest.mark.asyncio
    async def test_returns_error_when_processing_result_not_found(self):
        # arrange
        flow = AnalysisFlow(session_id="sess-1")
        mock_processing = MagicMock()
        mock_processing.get_processing_result = AsyncMock(
            side_effect=ValueError("No result found for session")
        )

        # act
        response = await flow.initialize(
            processing_service=mock_processing,
            analysis_service=MagicMock(),
        )

        # assert
        assert response.action == DialogueAction.ERROR

    @pytest.mark.asyncio
    async def test_returns_error_when_analysis_generation_fails(self):
        # arrange
        flow = AnalysisFlow(session_id="sess-1")
        mock_processing = MagicMock()
        mock_processing.get_processing_result = AsyncMock(return_value=_make_processing_result())
        mock_analysis = MagicMock()
        mock_analysis.generate_draft = AsyncMock(side_effect=Exception("AI failure"))

        # act
        response = await flow.initialize(
            processing_service=mock_processing,
            analysis_service=mock_analysis,
        )

        # assert
        assert response.action == DialogueAction.ERROR

    @pytest.mark.asyncio
    async def test_sets_state_to_complete_on_success(self):
        # arrange
        flow = AnalysisFlow(session_id="sess-1")
        mock_processing = MagicMock()
        mock_processing.get_processing_result = AsyncMock(return_value=_make_processing_result())
        mock_analysis = MagicMock()
        mock_analysis.generate_draft = AsyncMock(
            return_value=(_make_analysis_draft(), _make_processing_result())
        )

        # act
        response = await flow.initialize(
            processing_service=mock_processing,
            analysis_service=mock_analysis,
        )

        # assert
        assert flow.state == AnalysisState.COMPLETE
        assert response.action == DialogueAction.SHOW_ANALYSIS


class TestProcessUserMessage:
    @pytest.mark.asyncio
    async def test_returns_cached_analysis_when_state_is_complete(self):
        # arrange
        flow = AnalysisFlow(session_id="sess-1")
        flow.state = AnalysisState.COMPLETE
        flow.analysis_result = {"analysis": "data"}

        # act
        response = await flow.process_user_message()

        # assert
        assert response.action == DialogueAction.SHOW_ANALYSIS

    @pytest.mark.asyncio
    async def test_returns_error_when_analysis_not_ready(self):
        # arrange
        flow = AnalysisFlow(session_id="sess-1")
        flow.state = AnalysisState.PENDING

        # act
        response = await flow.process_user_message()

        # assert
        assert response.action == DialogueAction.ERROR
