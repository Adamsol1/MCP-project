from abc import ABC, abstractmethod
from datetime import datetime

from src.models.reasoning import ReasoningLogEntry, UserActionLogEntry


class BasePhaseFlow(ABC):
    """Base class for all phase flows (Direction, Collection, Processing).
    Provides shared logging helpers and enforces the process_user_message interface."""

    def __init__(self, session_id: str | None = None, research_logger=None):
        self.session_id = session_id
        self.research_logger = research_logger
        self.question_count = 0
        self.max_questions = 15

    # TODO: Remove when DB migration is complete — replaced by DB write
    def _log_reasoning(self, phase: str, attempt_number: int, generated_content: str, generation_duration: float, review_duration: float, model_used: str, review_result=None, error_type: str | None = None):
        log_entry = ReasoningLogEntry(
            session_id=self.session_id,
            phase=phase,
            attempt_number=attempt_number,
            timestamp=datetime.now(),
            generated_content=generated_content,
            generation_duration=generation_duration,
            review_result=review_result,
            review_duration=review_duration,
            model_used=model_used,
            error_type=error_type,
        )
        if self.research_logger:
            self.research_logger.create_log(log_entry)

    # TODO: Remove when DB migration is complete — replaced by DB write
    def _log_user_action(self, action, phase, modifications, perspectives=None):
        log_user_interaction = UserActionLogEntry(
            session_id=self.session_id,
            timestamp=datetime.now(),
            action=action,
            phase=phase,
            modifications=modifications,
            perspectives_selected=[p.value for p in perspectives] if perspectives else None,
        )
        if self.research_logger:
            self.research_logger.create_log(log_user_interaction)

    @abstractmethod
    async def process_user_message(self):
        """Process a single user message and return a DialogueResponse.
        Each phase flow implements this to drive its own state machine."""




