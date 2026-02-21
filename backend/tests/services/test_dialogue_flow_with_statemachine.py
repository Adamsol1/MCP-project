import pytest

from src.models.dialogue import ClarifyingQuestion, QuestionResult
from src.services.dialogue_flow import DialogueFlow, DialogueState


class MockDialogueService:
  async def generate_clarifying_question(self, user_message, context):  # noqa: ARG002
    question = ClarifyingQuestion(question_text="What is your scope", question_type="scope")
    return QuestionResult(question=question, extracted_context={})

  async def generate_pir(self, context, modifications=None):  # noqa: ARG002
    return "Generated PIR content"


#Test for checking if state machine starts in correct state
def test_correct_starting_state_for_dialogue_flow():
  dialogue_flow = DialogueFlow()
  assert dialogue_flow.state == DialogueState.INITIAL


#Test for checking if the machine state follows the intended path of initial -> gathering
@pytest.mark.asyncio
async def test_state_transition_from_initial_to_gathering():
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()

  result = await dialogue_flow.process_user_message("Investigate x", mock_service)

  assert dialogue_flow.state == DialogueState.GATHERING
  assert dialogue_flow.context.initial_query == "Investigate x"
  assert result.action == "ask_question"


#Test for checking if the machine states follow the intended path of gathering -> summary_confirming
@pytest.mark.asyncio
async def test_state_transition_from_gathering_to_summary_confirming():
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()

  dialogue_flow.state = DialogueState.GATHERING
  dialogue_flow.context.scope = "identify attack patterns"
  dialogue_flow.context.timeframe = "last 6 months"
  dialogue_flow.context.target_entities = ["Norway"]
  dialogue_flow.context.threat_actors = ["APT29"]
  dialogue_flow.context.priority_focus = "attack vectors"


  result = await dialogue_flow.process_user_message("Investigate x", mock_service)

  assert result.action == "show_summary"
  assert dialogue_flow.state == DialogueState.SUMMARY_CONFIRMING


#Test for checking summary_confirming -> pir_confirming when user approves summary
@pytest.mark.asyncio
async def test_state_transition_from_summary_confirming_to_pir_confirming():
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()

  dialogue_flow.state = DialogueState.SUMMARY_CONFIRMING

  result = await dialogue_flow.process_user_message("", mock_service, approved=True)

  assert result.action == "show_pir"
  assert dialogue_flow.state == DialogueState.PIR_CONFIRMING


#Test for checking summary_confirming stays when user rejects with modifications
@pytest.mark.asyncio
async def test_state_stays_summary_confirming_on_reject():
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()

  dialogue_flow.state = DialogueState.SUMMARY_CONFIRMING

  result = await dialogue_flow.process_user_message("add China to targets", mock_service, approved=False)

  assert result.action == "show_summary"
  assert dialogue_flow.state == DialogueState.SUMMARY_CONFIRMING
  assert dialogue_flow.context.modifications == "add China to targets"


#Test for checking pir_confirming -> complete when user approves PIR
@pytest.mark.asyncio
async def test_state_transition_from_pir_confirming_to_complete():
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()

  dialogue_flow.state = DialogueState.PIR_CONFIRMING

  result = await dialogue_flow.process_user_message("", mock_service, approved=True)

  assert result.action == "complete"
  assert dialogue_flow.state == DialogueState.COMPLETE


#Test for checking pir_confirming stays when user rejects with modifications
@pytest.mark.asyncio
async def test_state_stays_pir_confirming_on_reject():
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()

  dialogue_flow.state = DialogueState.PIR_CONFIRMING

  result = await dialogue_flow.process_user_message("focus more on TTPs", mock_service, approved=False)

  assert result.action == "show_pir"
  assert dialogue_flow.state == DialogueState.PIR_CONFIRMING
  assert dialogue_flow.context.modifications == "focus more on TTPs"


#Test for checking that the machine state is force changed from GATHERING -> SUMMARY_CONFIRMING when question count reaches max
@pytest.mark.asyncio
async def test_state_transition_when_question_count_is_max():
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()
  dialogue_flow.state = DialogueState.GATHERING

  dialogue_flow.question_count = dialogue_flow.max_questions

  result = await dialogue_flow.process_user_message("modify", mock_service)

  assert result.action == "max_questions"
  assert result.content is not None
  assert dialogue_flow.state == DialogueState.SUMMARY_CONFIRMING


#Test for checking that state stays on GATHERING when context is insufficient.
@pytest.mark.asyncio
async def test_state_stays_gathering_when_context_is_insufficient():
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()
  dialogue_flow.state = DialogueState.GATHERING

  result = await dialogue_flow.process_user_message("some input", mock_service)

  assert dialogue_flow.state == DialogueState.GATHERING
  assert result.action == "ask_question"
