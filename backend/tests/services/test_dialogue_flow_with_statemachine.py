import pytest
from src.services.dialogue_flow import DialogueFlow, DialogueState

class MockDialogueService():
  async def generate_clarifying_question(self, user_message, context):
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
  result = await dialogue_flow.process_user_input("Investigate x", mock_service)

  #Check if state is correct
  assert dialogue_flow.state == DialogueState.GATHERING


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
  result = await dialogue_flow.process_user_input("Ivestigate x", mock_service)

  assert dialogue_flow.state == DialogueState.CONFIRMING

#Test for checking if the machine states follow the intended path of human validation -> complete.
#Requires that the human accepts the information gathered in the GATHERING state
@pytest.mark.asyncio
async def test_state_transition_from_human_validation_to_complete():
  #Start new work flow for test enviorment
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()


  #Manually set state to CONFIRMING
  dialogue_flow.state = DialogueState.CONFIRMING

  #The user acccepts the information
  result = await dialogue_flow.process_user_input("yes", mock_service)

  assert dialogue_flow.state == DialogueState.COMPLETE

#Test for cheking if the machines state follow the inteded path of human validation -> GATHERING
#Requires that the human denies the information gathered in GATHERING state
@pytest.mark.asyncio
async def test_state_transition_from_human__validation_to_gathering():
  ##Start new work flow for test enviorment
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()


  #Manually set state to CONFIRMING
  dialogue_flow.state = DialogueState.CONFIRMING

  ##The user denies the information

  result = await dialogue_flow.process_user_input("no", mock_service)

  assert dialogue_flow.state == DialogueState.GATHERING

#Test for checking if the machine state follow the intended path of human validation -> Gathering with wanted modifications
#Requires that the human denies the information gathered in GATHERING state with input on what to change
@pytest.mark.asyncio
async def test_state_transition_from_human_validation_to_gathering_with_modifications():
  #Start new workflow for test enviorment
  dialogue_flow = DialogueFlow()
  mock_service = MockDialogueService()


  #Manually set state to CONFIRMING
  dialogue_flow.state = DialogueState.CONFIRMING

  ##The user denies the information and gives modifications
  result = await dialogue_flow.process_user_input("modify", mock_service)

  assert dialogue_flow.state == DialogueState.GATHERING








