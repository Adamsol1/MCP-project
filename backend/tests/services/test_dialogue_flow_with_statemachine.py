import pytest

from src.models.dialogue import ClarifyingQuestion, QuestionResult
from src.services.state_machines.direction_flow import DirectionFlow, DirectionState


class MockDialogueService:
    def __init__(self):
        self.clarifying_calls = []
        self.pir_calls = []
        self.summary_calls = []

    async def generate_clarifying_question(
        self, user_message, context, language="en"
    ):  # noqa: ARG002
        self.clarifying_calls.append(
            {
                "user_message": user_message,
                "language": language,
            }
        )
        question = ClarifyingQuestion(
            question_text="What is your scope",
            question_type="scope",
        )
        return QuestionResult(question=question, extracted_context={})

    async def generate_pir(
        self,
        context,
        modifications=None,
        language=None,
        current_pir=None,
    ):  # noqa: ARG002
        self.pir_calls.append(
            {
                "language": language,
                "current_pir": current_pir,
                "modifications": modifications,
            }
        )
        return "Generated PIR content"

    async def generate_summary(
        self,
        context,
        modifications=None,
        language="en",
    ):  # noqa: ARG002
        self.summary_calls.append(
            {
                "language": language,
                "modifications": modifications,
            }
        )
        return {"summary": "Mock summary"}


def test_correct_starting_state_for_dialogue_flow():
    dialogue_flow = DirectionFlow()
    assert dialogue_flow.state == DirectionState.INITIAL


@pytest.mark.asyncio
async def test_state_transition_from_initial_to_gathering():
    dialogue_flow = DirectionFlow()
    mock_service = MockDialogueService()

    result = await dialogue_flow.process_user_message("Investigate x", mock_service)

    assert dialogue_flow.state == DirectionState.GATHERING
    assert dialogue_flow.context.initial_query == "Investigate x"
    assert result.action == "ask_question"
    assert mock_service.clarifying_calls[0]["language"] == "en"


@pytest.mark.asyncio
async def test_state_transition_from_gathering_to_summary_confirming():
    dialogue_flow = DirectionFlow()
    mock_service = MockDialogueService()

    dialogue_flow.state = DirectionState.GATHERING
    dialogue_flow.context.scope = "identify attack patterns"
    dialogue_flow.context.timeframe = "last 6 months"
    dialogue_flow.context.target_entities = ["Norway"]
    dialogue_flow.context.threat_actors = ["APT29"]
    dialogue_flow.context.priority_focus = "attack vectors"

    result = await dialogue_flow.process_user_message("Investigate x", mock_service)

    assert result.action == "show_summary"
    assert dialogue_flow.state == DirectionState.SUMMARY_CONFIRMING
    assert mock_service.summary_calls[0]["language"] == "en"


@pytest.mark.asyncio
async def test_state_transition_from_summary_confirming_to_pir_confirming():
    dialogue_flow = DirectionFlow()
    mock_service = MockDialogueService()

    dialogue_flow.state = DirectionState.SUMMARY_CONFIRMING

    result = await dialogue_flow.process_user_message("", mock_service, approved=True)

    assert result.action == "show_pir"
    assert dialogue_flow.state == DirectionState.PIR_CONFIRMING
    assert mock_service.pir_calls[0]["language"] == "en"


@pytest.mark.asyncio
async def test_state_stays_summary_confirming_on_reject():
    dialogue_flow = DirectionFlow()
    mock_service = MockDialogueService()

    dialogue_flow.state = DirectionState.SUMMARY_CONFIRMING

    result = await dialogue_flow.process_user_message(
        "add China to targets",
        mock_service,
        approved=False,
    )

    assert result.action == "show_summary"
    assert dialogue_flow.state == DirectionState.SUMMARY_CONFIRMING
    assert dialogue_flow.context.modifications == "add China to targets"
    assert mock_service.summary_calls[0]["language"] == "en"
    assert mock_service.summary_calls[0]["modifications"] == "add China to targets"


@pytest.mark.asyncio
async def test_state_transition_from_pir_confirming_to_complete():
    dialogue_flow = DirectionFlow()
    mock_service = MockDialogueService()

    dialogue_flow.state = DirectionState.PIR_CONFIRMING

    result = await dialogue_flow.process_user_message("", mock_service, approved=True)

    assert result.action == "complete"
    assert dialogue_flow.state == DirectionState.COMPLETE


@pytest.mark.asyncio
async def test_state_stays_pir_confirming_on_reject():
    dialogue_flow = DirectionFlow()
    mock_service = MockDialogueService()

    dialogue_flow.state = DirectionState.PIR_CONFIRMING

    result = await dialogue_flow.process_user_message(
        "focus more on TTPs",
        mock_service,
        approved=False,
    )

    assert result.action == "show_pir"
    assert dialogue_flow.state == DirectionState.PIR_CONFIRMING
    assert dialogue_flow.context.modifications == "focus more on TTPs"
    assert mock_service.pir_calls[0]["language"] is None
    assert mock_service.pir_calls[0]["current_pir"] is None


@pytest.mark.asyncio
async def test_state_transition_when_question_count_is_max():
    dialogue_flow = DirectionFlow()
    mock_service = MockDialogueService()
    dialogue_flow.state = DirectionState.GATHERING

    dialogue_flow.question_count = dialogue_flow.max_questions

    result = await dialogue_flow.process_user_message("modify", mock_service)

    assert result.action == "max_questions"
    assert result.content is not None
    assert dialogue_flow.state == DirectionState.SUMMARY_CONFIRMING


@pytest.mark.asyncio
async def test_state_stays_gathering_when_context_is_insufficient():
    dialogue_flow = DirectionFlow()
    mock_service = MockDialogueService()
    dialogue_flow.state = DirectionState.GATHERING

    result = await dialogue_flow.process_user_message("some input", mock_service)

    assert dialogue_flow.state == DirectionState.GATHERING
    assert result.action == "ask_question"
    assert mock_service.clarifying_calls[0]["language"] == "en"
