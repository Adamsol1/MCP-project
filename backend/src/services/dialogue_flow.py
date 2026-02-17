from enum import Enum

from src.models.dialogue import DialogueContext, DialogueResponse, Perspective


class DialogueState(str, Enum):
  INITIAL = "initial" #State before first user input
  GATHERING = "gathering" #State when gathering information through questions
  SUMMARY_CONFIRMING = "summary_confirming" #Presenting context summary. User can approve or reject with modifications
  PIR_CONFIRMING = "pir_confirming" #Presenting generated PIR. User can approve or reject with modifications
  COMPLETE = "complete" #Direction phase complete. PIR approved


class DialogueFlow:
  def __init__(self):
    self.state = DialogueState.INITIAL #Starting with first state
    self.context = DialogueContext() #Context for information used in dialogue
    self.question_count = 0 #Counter for questions
    self.max_questions = 15 #Max number of questions. Prevents infinite loops



  def update_perspectives(self, perspectives: list[str]):
    """Update context perspectives from frontend selection.
    Converts string values (e.g. 'US') to Perspective enum values (e.g. 'us')."""
    self.context.perspectives = [
      Perspective(p.lower()) for p in perspectives
    ]

  async def process_user_message(self, user_message, dialogue_service, perspectives: list[str] | None = None, approved: bool | None = None) -> DialogueResponse:
    # Update perspectives on every message if provided
    if perspectives:
      self.update_perspectives(perspectives)
    #INITIAL PHASE
    if self.state == DialogueState.INITIAL:
      return await self.handle_initial_input(user_message, dialogue_service)

    #GATHERING PHASE
    elif self.state == DialogueState.GATHERING:
      return await self.handle_gathering_input(user_message, dialogue_service)

    #SUMMARY CONFIRMING PHASE
    elif self.state == DialogueState.SUMMARY_CONFIRMING:
      return await self.handle_summary_confirming(user_message, dialogue_service, approved)

    #PIR CONFIRMING PHASE
    elif self.state == DialogueState.PIR_CONFIRMING:
      return await self.handle_pir_confirming(user_message, dialogue_service, approved)

    #COMPLETE - should not receive messages in this state
    else:
      return DialogueResponse(action="complete", content="Direction phase already complete.")


  #State handler for initial phase. Here we will save initial query, generate questions and change state
  async def handle_initial_input(self, user_message, dialogue_service):
      self.context.initial_query = user_message #First user input is saved as initial query. This is the intended goal of the investigation
      #Create response that is sent to frontend
      dialogue_response = DialogueResponse()
      dialogue_response.action = "ask_question"

      #Generate questions for user based on user_message
      question = await dialogue_service.generate_clarifying_question(
          user_message=user_message,
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
  async def handle_gathering_input(self, user_message, dialogue_service):
      dialogue_response = DialogueResponse()
      if(self.question_count >= self.max_questions):
         self.state = DialogueState.SUMMARY_CONFIRMING
         dialogue_response.action = "max_questions"
         return dialogue_response

      #Generate question and update context (context is updated as side effect inside dialogue_service)
      question = await dialogue_service.generate_clarifying_question(
        user_message=user_message,
        context = self.context
       )
      self.question_count += 1

      #Change state GATHERING -> SUMMARY_CONFIRMING if possible
      if(self._has_sufficient_context()):
        self.state = DialogueState.SUMMARY_CONFIRMING
        dialogue_response.action = "show_summary"
        dialogue_response.content = self.context.model_dump_json()
        return dialogue_response
      else:
        #Context not sufficient, ask the generated question
        dialogue_response.action = "ask_question"
        dialogue_response.content = question.question_text
        return dialogue_response


  #State handler for summary confirming phase.
  #Frontend sends approved=True for approve, or user_message with modifications for reject.
  #Possible outcomes:
  # - Approve (approved=True) -> Generate PIR -> SUMMARY_CONFIRMING -> PIR_CONFIRMING
  # - Reject (approved=False/None + user_message) -> Save modifications, self-loop (stay in SUMMARY_CONFIRMING)
  async def handle_summary_confirming(self, user_message, dialogue_service, approved: bool | None = None):
      dialogue_response = DialogueResponse()

      if approved:
        #User approved context summary. Generate PIR and move to PIR_CONFIRMING
        pir = await dialogue_service.generate_pir(self.context)
        self.state = DialogueState.PIR_CONFIRMING
        dialogue_response.action = "show_pir"
        dialogue_response.content = pir
      else:
        #User rejected with modifications. Save and self-loop
        self.context.modifications = user_message
        dialogue_response.action = "show_summary"
        dialogue_response.content = self.context.model_dump_json()

      return dialogue_response


  #State handler for PIR confirming phase.
  #Frontend sends approved=True for approve, or user_message with modifications for reject.
  #Possible outcomes:
  # - Approve (approved=True) -> PIR_CONFIRMING -> COMPLETE
  # - Reject (approved=False/None + user_message) -> Regenerate PIR with modifications, self-loop (stay in PIR_CONFIRMING)
  async def handle_pir_confirming(self, user_message, dialogue_service, approved: bool | None = None):
      dialogue_response = DialogueResponse()

      if approved:
        #User approved PIR. Direction phase complete
        self.state = DialogueState.COMPLETE
        dialogue_response.action = "complete"
      else:
        #User rejected with modifications. Regenerate PIR
        self.context.modifications = user_message
        pir = await dialogue_service.generate_pir(self.context)
        dialogue_response.action = "show_pir"
        dialogue_response.content = pir

      return dialogue_response





  def _has_sufficient_context(self) -> bool:
   #List of fields required for context to be deemed sufficient
    context_fields = ["scope", "timeframe", "target_entities"]
    #Check if we have enough context. return bool
    for field in context_fields:  # noqa: SIM110
      if not getattr(self.context, field):
        return False
    return True
