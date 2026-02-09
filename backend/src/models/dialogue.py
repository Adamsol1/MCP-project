from enum import Enum

from pydantic import BaseModel


class QuestionType(str, Enum):
    SCOPE = "scope"
    TIMEFRAME = "timeframe"
    TARGETS = "target_entities"
    ACTORS = "actors"
    FOCUS = "focus"
    CONFIRMATION = "confirmation"


class DialogueContext(BaseModel):
    """Accumulates information gathered through dialogue"""

    initial_query: str = ""
    scope: str = ""
    timeframe: str = ""
    target_entities: list[str] = []
    threat_actors: list[str] | None = None
    priority_focus: str | None = None


class DialogueResponse(BaseModel):
    """Response object returned by dialogue flow to frontend"""

    action: str = ""
    content: str = ""


class ClarifyingQuestion(BaseModel):
    """Question returned by DialogueService"""

    question_text: str
    question_type: str
    is_final: bool = False
    suggested_answers: list[str] | None = None
