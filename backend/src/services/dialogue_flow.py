import json
import logging
from datetime import datetime
from enum import Enum

from src.models.dialogue import DialogueContext, DialogueResponse, Perspective
from src.models.reasoning import ReasoningLog, UserActionLogEntry

logger = logging.getLogger("app")

"TODO= lag generic phase class for each of the phases. e.g directionFlow."


class DialogueState(str, Enum):
    INITIAL = "initial"  # State before first user input
    GATHERING = "gathering"  # State when gathering information through questions
    SUMMARY_CONFIRMING = "summary_confirming"  # Presenting context summary. User can approve or reject with modifications
    PIR_CONFIRMING = "pir_confirming"  # Presenting generated PIR. User can approve or reject with modifications
    COMPLETE = "complete"  # Direction phase complete. PIR approved


class DialogueFlow:
    """
    State machine that drives the intelligence direction dialogue. Indicates and changes what state of the direction dialogue we are in

    States:  INITIAL -> GATHERING -> SUMMARY_CONFIRMING -> PIR_CONFIRMING -> COMPLETE

    Each state has a dedicated handler (e.g handle_gathering_input).
    All state transistions happens in these handlers.
    """

    def __init__(self, session_id: str | None = None, research_logger=None):
        self.state = DialogueState.INITIAL  # Starting with first state
        self.context = DialogueContext()  # Context for information used in dialogue
        self.question_count = 0  # Counter for questions
        self.max_questions = 15  # Max number of questions. Prevents infinite loops
        self.session_id = session_id
        self.research_logger = research_logger
        self.pending_reasoning_log: ReasoningLog | None = None
        self.current_pir: str | None = None
        logger.info(f"[Session {session_id}] Session started")

    def update_perspectives(self, perspectives: list[str]):
        """Update context perspectives from frontend selection.
        Converts string values (e.g. 'US') to Perspective enum values (e.g. 'us')."""
        self.context.perspectives = [Perspective(p.lower()) for p in perspectives]

    async def process_user_message(
        self,
        user_message,
        dialogue_service,
        perspectives: list[str] | None = None,
        approved: bool | None = None,
        orchestrator=None,
        reviewer=None,
        language: str = "en",
        settings_timeframe: str = "",
    ) -> DialogueResponse:
        """
        Route the incoming message to the correct state.

        Args:
            user_message: The message sent by the user.
            dialogue_service: Service for generating questions, summaries, and PIRs.
            perspectives: List of geopolitical perspectives from the frontend.
            approved: True = user accepts AI output, False/None = user rejects.
            orchestrator: If provided, uses the generate-and-review loop for PIR generation.
            reviewer: Required alongside orchestrator for PIR review.
            language: BCP-47 language code (e.g. "en", "no") — forwarded to MCP tools
                      so Gemini generates all responses in the selected language.
            settings_timeframe: Pre-set timeframe from the user's Settings → Parameters
                                 (e.g. "Last 30 days"). Pre-fills context.timeframe when
                                 it is currently empty, skipping the timeframe question.
        """
        # Update perspectives on every message if provided
        if perspectives:
            self.update_perspectives(perspectives)

        # Pre-fill timeframe from settings if not yet gathered through dialogue.
        # User input in chat always wins — _apply_context_update will overwrite this
        # later if the AI extracts an explicit timeframe from the conversation.
        if settings_timeframe.strip() and not self.context.timeframe:
            self.context.timeframe = settings_timeframe.strip()
            logger.info(
                f"[Session {self.session_id}] Timeframe pre-populated from settings: '{self.context.timeframe}'"
            )

        # INITIAL PHASE
        if self.state == DialogueState.INITIAL:
            return await self.handle_initial_input(user_message, dialogue_service, language)

        # GATHERING PHASE
        elif self.state == DialogueState.GATHERING:
            return await self.handle_gathering_input(user_message, dialogue_service, language)

        # SUMMARY CONFIRMING PHASE
        elif self.state == DialogueState.SUMMARY_CONFIRMING:
            return await self.handle_summary_confirming(
                user_message, dialogue_service, approved, orchestrator, reviewer, language
            )

        # PIR CONFIRMING PHASE
        elif self.state == DialogueState.PIR_CONFIRMING:
            return await self.handle_pir_confirming(
                user_message, dialogue_service, approved, language
            )

        # COMPLETE - should not receive messages in this state
        else:
            return DialogueResponse(
                action="complete", content="Direction phase already complete."
            )

    def _apply_context_update(self, extracted_context: dict):
        """Apply extracted context fields from MCP tool response to self.context.
        DialogueFlow owns all context state — this is the single place where context is updated."""
        if extracted_context.get("scope"):
            self.context.scope = extracted_context["scope"]
        if extracted_context.get("timeframe"):
            self.context.timeframe = extracted_context["timeframe"]
        if extracted_context.get("target_entities"):
            self.context.target_entities = extracted_context["target_entities"]
        if extracted_context.get("threat_actors"):
            self.context.threat_actors = extracted_context["threat_actors"]
        if extracted_context.get("priority_focus"):
            self.context.priority_focus = extracted_context["priority_focus"]

    async def handle_initial_input(
        self, user_message, dialogue_service, language: str = "en"
    ) -> DialogueResponse:
        """
        State handler for initial phase. Here we will save initial query, generate questions and change state to GATHERING
        Possible state changes: INITIAL -> GATHERING
        """
        self.context.initial_query = user_message  # First user input is saved as initial query. This is the intended goal of the investigation
        # Create response that is sent to frontend
        dialogue_response = DialogueResponse()
        dialogue_response.action = "ask_question"

        # Generate question and extract context from user message
        result = await dialogue_service.generate_clarifying_question(
            user_message=user_message, context=self.context, language=language
        )
        # Update context
        self._apply_context_update(result.extracted_context)
        dialogue_response.content = result.question.question_text
        self.context.dialogue_turns.append(
            {
                "question": result.question.question_text,
                "answer": user_message,
            }
        )
        # Increase counter
        self.question_count += 1
        # Change state INITIAL -> GATHERING
        self.state = DialogueState.GATHERING
        logger.info(f"[Session {self.session_id}] State: INITIAL -> GATHERING")

        # Return response to frontend
        return dialogue_response

    async def handle_gathering_input(
        self, user_message, dialogue_service, language: str = "en"
    ) -> DialogueResponse:
        """
        State handler for gathering phase.  Here we will update context with information from user input.
          If we have enough context after updating context change state
          If we do not have enough context return a follow up question

         Possible state transitions:
          -If enough context: GATHERING -> SUMMARY_CONFIRMING
          -If not enough context rejects: GATHERING -> GATHERING
          -If AI have reached more than 15 questions, enforce state change to prevent AI loops : GATHERING -> SUMMARY_CONFIRMING

        """
        dialogue_response = DialogueResponse()
        # If we reach max questions, force state change.
        if self.question_count >= self.max_questions:
            self.state = DialogueState.SUMMARY_CONFIRMING
            logger.info(
                f"[Session {self.session_id}] State: GATHERING -> SUMMARY_CONFIRMING (max questions reached)"
            )
            dialogue_response.action = "max_questions"
            # TODO: Replace model_dump_json with generate_summary MCP call when implemented:
            # summary = await dialogue_service.generate_summary(self.context)
            # dialogue_response.content = summary
            dialogue_response.content = self.context.model_dump_json()
            return dialogue_response

        # Generate question and extract context from user message
        result = await dialogue_service.generate_clarifying_question(
            user_message=user_message, context=self.context, language=language
        )
        # Update context
        self._apply_context_update(result.extracted_context)
        self.context.dialogue_turns.append(
            {
                "question": result.question.question_text,
                "answer": user_message,
            }
        )
        self.question_count += 1

        # Change state GATHERING -> SUMMARY_CONFIRMING if possible
        if self._has_sufficient_context():
            self.state = DialogueState.SUMMARY_CONFIRMING
            logger.info(
                f"[Session {self.session_id}] State: GATHERING -> SUMMARY_CONFIRMING (sufficient context)"
            )
            dialogue_response.action = "show_summary"
            summary = await dialogue_service.generate_summary(self.context, language=language)
            dialogue_response.content = (
                json.dumps(summary) if isinstance(summary, dict) else summary
            )
            return dialogue_response
        else:
            # Context not sufficient, ask the generated question
            dialogue_response.action = "ask_question"
            dialogue_response.content = result.question.question_text
            return dialogue_response

    async def handle_summary_confirming(
        self,
        user_message,
        dialogue_service,
        approved: bool | None = None,
        orchestrator=None,
        reviewer=None,
        language: str = "en",
    ) -> DialogueResponse:
        """
        State handler for summary confirming phase.
        Frontend sends approved=True for approve, or user_message with modifications for reject.
        Possible outcomes:
          - Approve (approved=True) -> Generate PIR -> SUMMARY_CONFIRMING -> PIR_CONFIRMING
          - Reject (approved=False/None + user_message) -> Save modifications, self-loop (stay in SUMMARY_CONFIRMING)
        """
        dialogue_response = DialogueResponse()

        if approved:
            # User approved context summary. Generate PIR and move to PIR_CONFIRMING
            # If orchestrator and reviewer are provided, use the full generate+review loop.
            # Bridge: store language on the service instance so the orchestrator path
            # (which calls dialogue_service.generate_pir(context) with only one arg) can
            # still pick up the correct language without touching the orchestrator API.
            dialogue_service.language = language
            if orchestrator and reviewer:
                pir = await orchestrator.generate_and_review_pir(
                    self.context,
                    dialogue_service,
                    reviewer,
                    phase="direction",
                    session_id=self.session_id,
                )
            # If no orchestator just generate pir alone
            else:
                pir = await dialogue_service.generate_pir(self.context, language=language)
            self.current_pir = json.dumps(pir) if isinstance(pir, dict) else pir
            if orchestrator:
                retry_count = len(orchestrator.generated_pirs) - 1
                self.pending_reasoning_log = ReasoningLog(
                    session_id=self.session_id,
                    model_used=orchestrator.generator_model,
                    dialogue_turns=self.context.dialogue_turns,
                    generated_pirs_before_review=orchestrator.generated_pirs,
                    review_reasoning_per_pir=orchestrator.review_results,
                    retry_explanation=orchestrator.retry_explanations,
                    final_approved_pir=None,
                    timestamps={"pir_generated": datetime.now().isoformat()},
                    retry_triggered=retry_count > 0,
                    retry_count=retry_count,
                )
            log_user_interaction = UserActionLogEntry(
                session_id=self.session_id,
                timestamp=datetime.now(),
                action="approve",
                phase="summary_confirming",
                modifications=None,
                perspectives_selected=[p.value for p in self.context.perspectives],
            )
            if self.research_logger:
                self.research_logger.create_log(log_user_interaction)
            self.context.modifications = (
                None  # Clear modifications so they don't leak into PIR phase
            )
            self.state = DialogueState.PIR_CONFIRMING
            logger.info(
                f"[Session {self.session_id}] State: SUMMARY_CONFIRMING -> PIR_CONFIRMING"
            )
            dialogue_response.action = "show_pir"
            dialogue_response.content = (
                json.dumps(pir) if isinstance(pir, dict) else pir
            )
        else:
            # User rejected with modifications. Save and self-loop
            self.context.modifications = user_message
            log_user_interaction = UserActionLogEntry(
                session_id=self.session_id,
                timestamp=datetime.now(),
                action="reject",
                phase="summary_confirming",
                modifications=user_message,
                perspectives_selected=[p.value for p in self.context.perspectives],
            )
            if self.research_logger:
                self.research_logger.create_log(log_user_interaction)
            dialogue_response.action = "show_summary"
            summary = await dialogue_service.generate_summary(
                self.context, modifications=user_message, language=language
            )
            dialogue_response.content = (
                json.dumps(summary) if isinstance(summary, dict) else summary
            )

        return dialogue_response

    async def handle_pir_confirming(
        self, user_message, dialogue_service, approved: bool | None = None, language: str = "en"
    ) -> DialogueResponse:
        """
        State handler for PIR confirming phase.
        Frontend sends approved=True for approve, or user_message with modifications for reject.
        Possible outcomes:
         - Approve (approved=True) -> PIR_CONFIRMING -> COMPLETE
         - Reject (approved=False/None + user_message) -> Regenerate PIR with modifications, self-loop (stay in PIR_CONFIRMING)
        """
        dialogue_response = DialogueResponse()

        if approved:
            # User approved PIR. Direction phase complete
            log_user_interaction = UserActionLogEntry(
                session_id=self.session_id,
                timestamp=datetime.now(),
                action="approve",
                phase="pir_confirming",
                modifications=None,
                perspectives_selected=[p.value for p in self.context.perspectives],
            )
            if self.research_logger:
                self.research_logger.create_log(log_user_interaction)
            self.state = DialogueState.COMPLETE
            logger.info(
                f"[Session {self.session_id}] State: PIR_CONFIRMING -> COMPLETE. Direction phase finished"
            )
            if self.pending_reasoning_log and self.research_logger:
                self.pending_reasoning_log.final_approved_pir = self.current_pir
                self.pending_reasoning_log.timestamps["pir_approved"] = (
                    datetime.now().isoformat()
                )
                self.research_logger.write_reasoning_log(self.pending_reasoning_log)
            dialogue_response.action = "complete"
        else:
            # User rejected with modifications. Regenerate PIR
            self.context.modifications = user_message
            log_user_interaction = UserActionLogEntry(
                session_id=self.session_id,
                timestamp=datetime.now(),
                action="reject",
                phase="pir_confirming",
                modifications=user_message,
                perspectives_selected=[p.value for p in self.context.perspectives],
            )
            if self.research_logger:
                self.research_logger.create_log(log_user_interaction)
            pir = await dialogue_service.generate_pir(self.context, language=language)
            self.current_pir = json.dumps(pir) if isinstance(pir, dict) else pir
            dialogue_response.action = "show_pir"
            dialogue_response.content = self.current_pir

        return dialogue_response

    def _has_sufficient_context(self) -> bool:
        """
        Checks if we have enough context
        Return True if all five required fields are provied.
        Else return false
        """
        # List of fields required for context to be deemed sufficient
        context_fields = [
            "scope",
            "timeframe",
            "target_entities",
            "threat_actors",
            "priority_focus",
        ]
        # Check if we have enough context. return bool
        for field in context_fields:  # noqa: SIM110
            if not getattr(self.context, field):
                return False
        return True
