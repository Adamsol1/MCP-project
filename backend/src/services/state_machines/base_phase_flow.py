

from abc import ABC, abstractmethod
from datetime import datetime

from src.models.reasoning import UserActionLogEntry


class BasePhaseFlow(ABC):
  def __init__(self, session_id: str | None = None, research_logger=None):
    self.session_id = session_id
    self.research_logger = research_logger
    self.question_count = 0
    self.max_questions = 15



  def _log_user_action(self, action, phase, modifications, perspectives=None):
        log_user_interaction = UserActionLogEntry(
                session_id=self.session_id,
                timestamp=datetime.now(),
                action=action,
                phase=phase,
                modifications=modifications,
                perspectives_selected= [p.value for p in perspectives] if perspectives else None

            )
        if self.research_logger:
          self.research_logger.create_log(log_user_interaction)

  @abstractmethod
  async def process_user_message(self):
      """"""




