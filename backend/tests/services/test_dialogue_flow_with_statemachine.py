import pytest

from src.services.dialogue_flow import DialogueFlow, DialogueState


class MockDialogueService:
  async def generate_clarifying_question(self, user_message, context):  # noqa: ARG002
    return MockQuestion()

class MockQuestion:
  def __init__(self):
    self.question_text = "What is your scope"
    self.question_type = "scope"


#Test for checking if state machine starts in correct state
def test_correct_starting_state_for_dialogue_flow():
  #Start a new flow to create the correct enviorment for the test
  dialogue_flow = DialogueFlow()


  #Test if the start state is INITIAL
  assert dialogue_flow.state == DialogueState.INITIAL


#Test for checking if the machine state follows the intended path of initial -> gathering
@pytest.mark.asyncio #Marks the test as async
async def test_state_transition_from_initial_to_gathering():
  #Start new work flow for test enviorment
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()

  #Attempt to move to next state
  result = await dialogue_flow.process_user_message("Investigate x", mock_service)

  #Check if state is correct
  assert dialogue_flow.state == DialogueState.GATHERING
  #Check if initial query is saved
  assert dialogue_flow.context.initial_query == "Investigate x"
  #Check if UI is updated with correct action
  assert result.action == "ask_question"


#Test for checking if the machine states follow the inteded path of gathering -> confirming
@pytest.mark.asyncio
async def test_state_transition_from_gathering_to_confirming():
  #Start new work flow for test enviorment
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()

  #Manually edit the state to Gathering
  dialogue_flow.state = DialogueState.GATHERING

  #Set context for the dialogue
  dialogue_flow.context.scope = "identify attack patterns"
  dialogue_flow.context.timeframe = "last 6 months"
  dialogue_flow.context.target_entities = ["Norway"] #List of target entities

  #Attempt to move to the next state
  result = await dialogue_flow.process_user_message("Investigate x", mock_service)

  assert result.action == "show_summary"

  assert dialogue_flow.state == DialogueState.CONFIRMING

#Test for checking if the machine states follow the intended path of CONFIRMING -> COMPLETE.
#Requires that the human accepts the information gathered in the GATHERING state
@pytest.mark.asyncio
async def test_state_transition_from_confirming_to_complete():
  #Start new work flow for test enviorment
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()


  #Manually set state to CONFIRMING
  dialogue_flow.state = DialogueState.CONFIRMING

  #The user acccepts the information via the approved boolean flag
  result = await dialogue_flow.process_user_message("approve", mock_service, approved=True)

  assert result.action == "complete"

  assert dialogue_flow.state == DialogueState.COMPLETE

#Test for checking if the machine state follow the intended path of CONFIRMING -> GATHERING with wanted modifications
#Requires that the human denies the information gathered in GATHERING state with input on what to change
@pytest.mark.asyncio
async def test_state_transition_from_confirming_to_gathering_with_modifications():
  #Start new workflow for test enviorment
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()


  #Manually set state to CONFIRMING
  dialogue_flow.state = DialogueState.CONFIRMING

  ##The user denies the information and gives modifications
  result = await dialogue_flow.process_user_message(False, mock_service)

  assert result.action == "ask_modification"

  assert dialogue_flow.state == DialogueState.GATHERING


#Test for checking that the machine state is force changed from GATHERING -> CONFIRMING when question count reaches max
@pytest.mark.asyncio
async def test_state_transition_when_question_count_is_max():
  #Start new workflow for test enviorment and put in relevant state
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()
  dialogue_flow.state = DialogueState.GATHERING


  #Maually set question count to max and process user input
  dialogue_flow.question_count = dialogue_flow.max_questions

  result = await dialogue_flow.process_user_message("modify", mock_service)

  #Check if action is max_questions
  assert result.action == "max_questions"

  #Check if machine state is forced to CONFIRMING

  assert dialogue_flow.state == DialogueState.CONFIRMING

#Test for checking that state stays on GATHERING when context is insufficient.
@pytest.mark.asyncio
async def test_state_stays_gathering_when_context_is_insufficient():
  #Set new flow for test
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()
  dialogue_flow.state = DialogueState.GATHERING

  #No context set

  result = await dialogue_flow.process_user_message("some input", mock_service)

  #State should remain GATHERING
  assert dialogue_flow.state == DialogueState.GATHERING
  #Should ask for more info
  assert result.action == "ask_question"










