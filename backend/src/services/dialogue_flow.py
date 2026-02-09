from src.models.dialogue import DialogueContext, DialogueResponse


class DialogueState:
  INITIAL = "initial"#State before first user input
  GATHERING = "gathering" #State when gathering information through questions
  CONFIRMING = "confirming" #Presenting summary of gathering phase. Will ask if the user finds the result approvable.
  COMPLETE = "complete" #Ready for creating the priority intelligence requirements (PIR)


class DialogueFlow:
  def __init__(self):
    self.state = DialogueState.INITIAL #Starting with first state
    self.context = DialogueContext() #Context for information used in dialogue
    self.question_count = 0 #Counter for questions
    self.max_questions = 15 #Max number of questions. Prevents infinite loops



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
      self.context.initial_query = user_input #First user input is saved as initial query. This is the intended goal of the investigation
      #Create response that is sent to frontend
      dialogue_response = DialogueResponse()
      dialogue_response.action = "ask_question"

      #Generate questions for user based on user_input
      question = await dialogue_service.generate_clarifying_question(
          user_input=user_input,
          context = self.context
         )
      dialogue_response.content = question.question_text
      #Increase counter
      self.question_count += 1
      #Change state INITIAL -> GATHERING
      self.state = DialogueState.GATHERING

      #Return response to frontend
      return dialogue_response

  #State handler for gathering phase.  Here we will update context with information from user input, change state if possible or generate more questions if needed
  async def handle_gathering_input(self, user_input, dialogue_service):
      dialogue_response = DialogueResponse()
      if(self.question_count >= self.max_questions):
         self.state = DialogueState.CONFIRMING
         dialogue_response.action = "max_questions"
         return dialogue_response




      #Generate questions

      #Change state GATHERING -> CONFIRMING if possible
      if(self._has_sufficient_context()):
        self.state = DialogueState.CONFIRMING
        dialogue_response.action = "show_summary"
        self.question_count += 1
        return dialogue_response
      else:
        question = await dialogue_service.generate_clarifying_questions(
          user_input=user_input,
          context = self.context
         )
        dialogue_response.action = "ask_question"
        dialogue_response.content = question.question_text
        #Increase counter
        self.question_count += 1
        return dialogue_response


  #State handler for confirming phase. Here we check if user confirm/update/reject the investigation summary.
  #Possible outcomes:
# - User confirms the summary -> Change state CONFIRMING -> COMPLETE
# - User updates the summary -> Change state CONFIRMING -> GATHERING
# - User rejects the summary -> Change state CONFIRMING -> GATHERING

  async def handle_confirming_input(self, user_input, dialogue_service):

      #Set ut frontend response
      dialogue_respons = DialogueResponse()
      #Check if user confirms summary
      if user_input:
         self.state = DialogueState.COMPLETE
         dialogue_respons.action = "complete"


      else:
         self.state = DialogueState.GATHERING
         dialogue_respons.action = "ask_modification"

      #Return reponse to frontend
      return dialogue_respons





  def _has_sufficient_context(self) -> bool:
   #List of fields required for context to be deemed sufficient
    context_fields = ["scope", "timeframe", "target_entities"]
    #Check if we have enough context. return bool
    for field in context_fields:  # noqa: SIM110
      if not getattr(self.context, field):
        return False
    return True


