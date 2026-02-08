import src.models.dialogue
from src.models.dialogue import DialogueContext


class DialogueState:
  INITIAL = "initial", #State before first user input
  GATHERING = "gathering" #State when gathering information through questions
  CONFIRMING = "confirming" #Presenting summary of gathering phase. Will ask if the user finds the result approvable.
  COMPLETE = "complete" #Ready for creating the priority intelligence requirements (PIR)




class DialogueFlow:
  def __init__(self):
    self.state = DialogueState.INITIAL #Starting with first state
    self.context = DialogueContext() #Context for information used in dialogue


  async def process_user_input(self, user_input, dialogue_service):
    #INITIAL PHASE
    if self.state == DialogueState.INITIAL:
      return await self.handle_initial_input(user_input, dialogue_service)

    #GATHERIGN PHASE
    elif self.state == DialogueState.GATHERING:
      return await self.handle_gathering_input(user_input, dialogue_service)

    #CONFIRMING PHASE
    elif self.state == DialogueState.CONFIRMING:
      return await self.handle_confirming_input(user_input, dialogue_service)


  #State handler for initial phase. Here we will save initial query, generate questions and change state
  async def handle_initial_input(self, user_input, dialogue_service):
      temp = user_input
      self.context.initial_query = user_input #First user input is saved as initial query. This is the intended goal of the investigation

      #Generate questions for user

      #Change state INITIAL -> GATHERING
      self.state = DialogueState.GATHERING

  #State handler for gathering phase.  Here we will update context with information from user input, change state if possible or generate more questions if needed
  async def handle_gathering_input(self, user_input, dialogue_service):
      temp = user_input

      #Generate questions

      #Change state GATHERING -> CONFIRMING if possible
      self.state = DialogueState.CONFIRMING

  #State handler for confirming phase. Here we check if user confirm/update/reject the investigation summary.
  #Possible outcomes:
# - User confirms the summary -> Change state CONFIRMING -> COMPLETE
# - User updates the summary -> Change state CONFIRMING -> GATHERING
# - User rejects the summary -> Change state CONFIRMING -> GATHERING

  async def handle_confirming_input(self, user_input, dialogue_service):
      temp = user_input

      #Check if user confirms summary

      




