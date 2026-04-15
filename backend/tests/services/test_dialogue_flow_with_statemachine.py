import pytest

from src.models.dialogue import ClarifyingQuestion, QuestionResult
from src.services.state_machines.direction_flow import DirectionFlow, DirectionState


class MockDialogueService:
    def __init__(
        self,
        *,
        raise_on_clarifying: bool = False,
        raise_on_pir: bool = False,
        raise_on_summary: bool = False,
    ):
        self.clarifying_calls = []
        self.pir_calls = []
        self.summary_calls = []
        self.raise_on_clarifying = raise_on_clarifying
        self.raise_on_pir = raise_on_pir
        self.raise_on_summary = raise_on_summary

    async def generate_clarifying_question(
        self, user_message, context, language="en"
    ):
        del context
        if self.raise_on_clarifying:
            raise RuntimeError("Service unavailable")
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
    ):
        del context
        if self.raise_on_pir:
            raise RuntimeError("Service unavailable")
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
    ):
        del context
        if self.raise_on_summary:
            raise RuntimeError("Service unavailable")
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
    assert mock_service.pir_calls[0]["language"] == "en"
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


# ── Error handling ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_initial_input_returns_error_when_service_raises():
    # Arrange
    flow = DirectionFlow(session_id="test")
    mock_service = MockDialogueService(raise_on_clarifying=True)

    # Act
    result = await flow.process_user_message("Investigate x", mock_service)

    # Assert
    assert result.action == "error"
    assert flow.state == DirectionState.INITIAL  # state must not advance on error


@pytest.mark.asyncio
async def test_gathering_clarifying_returns_error_when_service_raises():
    # Arrange
    flow = DirectionFlow(session_id="test")
    mock_service = MockDialogueService(raise_on_clarifying=True)
    flow.state = DirectionState.GATHERING

    # Act
    result = await flow.process_user_message("some input", mock_service)

    # Assert
    assert result.action == "error"
    assert flow.state == DirectionState.GATHERING  # state must not advance on error


@pytest.mark.asyncio
async def test_gathering_generate_summary_returns_error_when_service_raises():
    # Arrange — all context fields filled so _has_sufficient_context() returns True
    flow = DirectionFlow(session_id="test")
    mock_service = MockDialogueService(raise_on_summary=True)
    flow.state = DirectionState.GATHERING
    flow.context.scope = "threat hunting"
    flow.context.timeframe = "last 6 months"
    flow.context.target_entities = ["Norway"]
    flow.context.threat_actors = ["APT29"]
    flow.context.priority_focus = "attack vectors"

    # Act
    result = await flow.process_user_message("some input", mock_service)

    # Assert
    assert result.action == "error"


@pytest.mark.asyncio
async def test_summary_confirming_approve_returns_error_when_pir_generation_fails():
    # Arrange
    flow = DirectionFlow(session_id="test")
    mock_service = MockDialogueService(raise_on_pir=True)
    flow.state = DirectionState.SUMMARY_CONFIRMING

    # Act
    result = await flow.process_user_message("", mock_service, approved=True)

    # Assert
    assert result.action == "error"
    assert flow.state == DirectionState.SUMMARY_CONFIRMING  # state must not advance on error


@pytest.mark.asyncio
async def test_summary_confirming_reject_returns_error_when_summary_fails():
    # Arrange
    flow = DirectionFlow(session_id="test")
    mock_service = MockDialogueService(raise_on_summary=True)
    flow.state = DirectionState.SUMMARY_CONFIRMING

    # Act
    result = await flow.process_user_message("add more detail", mock_service, approved=False)

    # Assert
    assert result.action == "error"


@pytest.mark.asyncio
async def test_pir_confirming_reject_returns_error_when_pir_regeneration_fails():
    # Arrange
    flow = DirectionFlow(session_id="test")
    mock_service = MockDialogueService(raise_on_pir=True)
    flow.state = DirectionState.PIR_CONFIRMING

    # Act
    result = await flow.process_user_message("focus on TTPs", mock_service, approved=False)

    # Assert
    assert result.action == "error"
    assert flow.state == DirectionState.PIR_CONFIRMING  # state must not advance on error


# ── Language parameter ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_language_forwarded_to_initial_input():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()

    # Act
    await flow.process_user_message("Investigate x", mock_service, language="no")

    # Assert
    assert mock_service.clarifying_calls[0]["language"] == "no"


@pytest.mark.asyncio
async def test_language_forwarded_to_gathering_input():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()
    flow.state = DirectionState.GATHERING

    # Act
    await flow.process_user_message("some input", mock_service, language="no")

    # Assert
    assert mock_service.clarifying_calls[0]["language"] == "no"


@pytest.mark.asyncio
async def test_language_forwarded_to_summary_confirming_approve():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()
    flow.state = DirectionState.SUMMARY_CONFIRMING

    # Act
    await flow.process_user_message("", mock_service, approved=True, language="no")

    # Assert — language is set on service instance (bridge for orchestrator path) and forwarded to generate_pir
    assert mock_service.language == "no"
    assert mock_service.pir_calls[0]["language"] == "no"


@pytest.mark.asyncio
async def test_language_forwarded_to_summary_confirming_reject():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()
    flow.state = DirectionState.SUMMARY_CONFIRMING

    # Act
    await flow.process_user_message("add more detail", mock_service, approved=False, language="no")

    # Assert
    assert mock_service.summary_calls[0]["language"] == "no"


# ── Perspectives ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_perspectives_updated_via_process_user_message():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()

    # Act
    await flow.process_user_message("Investigate x", mock_service, perspectives=["us", "eu"])

    # Assert
    assert len(flow.context.perspectives) == 2


def test_update_perspectives_converts_strings_to_enum():
    # Arrange
    flow = DirectionFlow()

    # Act
    flow.update_perspectives(["us", "eu"])

    # Assert
    assert len(flow.context.perspectives) == 2
    assert all(p.value in ("us", "eu") for p in flow.context.perspectives)


# ── settings_timeframe ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_settings_timeframe_prefills_empty_context():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()

    # Act
    await flow.process_user_message("Investigate x", mock_service, settings_timeframe="Last 30 days")

    # Assert
    assert flow.context.timeframe == "Last 30 days"


@pytest.mark.asyncio
async def test_settings_timeframe_does_not_overwrite_existing_timeframe():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()
    flow.context.timeframe = "Last 6 months"

    # Act
    await flow.process_user_message("Investigate x", mock_service, settings_timeframe="Last 30 days")

    # Assert — existing timeframe wins
    assert flow.context.timeframe == "Last 6 months"


# ── sub_state ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sub_state_set_to_awaiting_decision_after_summary_reject():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()
    flow.state = DirectionState.SUMMARY_CONFIRMING

    # Act
    await flow.process_user_message("add more detail", mock_service, approved=False)

    # Assert
    assert flow.sub_state == "awaiting_decision"


@pytest.mark.asyncio
async def test_sub_state_set_to_awaiting_decision_after_pir_reject():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()
    flow.state = DirectionState.PIR_CONFIRMING

    # Act
    await flow.process_user_message("focus on TTPs", mock_service, approved=False)

    # Assert
    assert flow.sub_state == "awaiting_decision"


@pytest.mark.asyncio
async def test_sub_state_cleared_on_pir_approve():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()
    flow.state = DirectionState.PIR_CONFIRMING
    flow.sub_state = "awaiting_decision"

    # Act
    await flow.process_user_message("", mock_service, approved=True)

    # Assert
    assert flow.sub_state is None


# ── COMPLETE state ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_complete_state_returns_complete_response():
    # Arrange
    flow = DirectionFlow()
    mock_service = MockDialogueService()
    flow.state = DirectionState.COMPLETE

    # Act
    result = await flow.process_user_message("anything", mock_service)

    # Assert
    assert result.action == "complete"


# ── get_debug_state ────────────────────────────────────────────────────────────

def test_get_debug_state_returns_expected_fields():
    # Arrange
    flow = DirectionFlow(session_id="test")
    flow.state = DirectionState.SUMMARY_CONFIRMING
    flow.context.scope = "threat hunting"
    flow.context.timeframe = "last 6 months"
    flow.context.target_entities = ["Norway"]
    flow.context.threat_actors = ["APT29"]
    flow.context.priority_focus = "attack vectors"

    # Act
    debug = flow.get_debug_state()

    # Assert
    assert debug["stage"] == "summary_confirming"
    assert debug["question_count"] == 0
    assert debug["max_questions"] == 15
    assert debug["missing_context_fields"] == []
    assert debug["has_sufficient_context"] is True
    assert debug["awaiting_user_decision"] is True
    assert debug["has_modifications"] is False


def test_get_debug_state_awaiting_user_decision_false_when_awaiting_modifications():
    # Arrange
    flow = DirectionFlow(session_id="test")
    flow.state = DirectionState.SUMMARY_CONFIRMING
    flow.sub_state = "awaiting_modifications"

    # Act
    debug = flow.get_debug_state()

    # Assert
    assert debug["awaiting_user_decision"] is False


def test_get_debug_state_reports_missing_fields():
    # Arrange
    flow = DirectionFlow(session_id="test")
    flow.state = DirectionState.GATHERING
    flow.context.scope = "threat hunting"
    # timeframe, target_entities, threat_actors, priority_focus all missing

    # Act
    debug = flow.get_debug_state()

    # Assert
    assert "timeframe" in debug["missing_context_fields"]
    assert debug["has_sufficient_context"] is False


# ── force_state ────────────────────────────────────────────────────────────────

def test_force_state_changes_state():
    # Arrange
    flow = DirectionFlow(session_id="test")

    # Act
    flow.force_state(DirectionState.GATHERING)

    # Assert
    assert flow.state == DirectionState.GATHERING


def test_force_state_seeds_context():
    # Arrange
    flow = DirectionFlow(session_id="test")

    # Act
    flow.force_state(DirectionState.GATHERING, seed_context={"scope": "test scope"})

    # Assert
    assert flow.context.scope == "test scope"


def test_force_state_ensures_minimum_context_for_confirm_states():
    # Arrange
    flow = DirectionFlow(session_id="test")
    # context is completely empty

    # Act
    flow.force_state(DirectionState.SUMMARY_CONFIRMING)

    # Assert — minimum context is seeded so confirm state is valid
    assert flow.context.scope != ""
    assert flow.context.timeframe != ""
    assert flow.context.target_entities


def test_force_state_resets_question_count_on_initial():
    # Arrange
    flow = DirectionFlow(session_id="test")
    flow.question_count = 10

    # Act
    flow.force_state(DirectionState.INITIAL)

    # Assert
    assert flow.question_count == 0
    assert flow.pending_reasoning_log is None


# ── to_dict / from_dict ────────────────────────────────────────────────────────

def test_to_dict_from_dict_roundtrip():
    # Arrange
    flow = DirectionFlow(session_id="test-session")
    flow.state = DirectionState.GATHERING
    flow.context.initial_query = "Investigate APT29"
    flow.context.scope = "threat hunting"
    flow.context.timeframe = "last 6 months"
    flow.question_count = 3
    flow.current_pir = '{"result": "test pir"}'

    # Act
    data = flow.to_dict()
    restored = DirectionFlow.from_dict(data)

    # Assert
    assert restored.session_id == "test-session"
    assert restored.state == DirectionState.GATHERING
    assert restored.context.initial_query == "Investigate APT29"
    assert restored.context.scope == "threat hunting"
    assert restored.context.timeframe == "last 6 months"
    assert restored.question_count == 3
    assert restored.current_pir == '{"result": "test pir"}'
    assert restored.pending_reasoning_log is None


def test_to_dict_from_dict_roundtrip_without_pir():
    # Arrange — INITIAL state, no PIR yet
    flow = DirectionFlow(session_id="no-pir-session")

    # Act
    data = flow.to_dict()
    restored = DirectionFlow.from_dict(data)

    # Assert
    assert restored.state == DirectionState.INITIAL
    assert restored.current_pir is None
    assert restored.pending_reasoning_log is None
