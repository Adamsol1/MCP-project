from enum import Enum
from typing import Literal

from pydantic import BaseModel



class Perspective(str, Enum):
    US = "us"
    NORWAY = "norway"
    CHINA = "china"
    EU = "eu"
    RUSSIA = "russia"
    NEUTRAL = "neutral"


class DialogueAction(str, Enum):
    ASK_QUESTION = "ask_question"
    SHOW_SUMMARY = "show_summary"
    SHOW_PIR = "show_pir"
    MAX_QUESTIONS = "max_questions"
    COMPLETE = "complete"


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
    perspectives: list[Perspective] = [Perspective.NEUTRAL]
    modifications: str | None = None
    dialogue_turns: list[dict] = []


class DialogueResponse(BaseModel):
    """Response object returned by dialogue flow to frontend"""

    action: DialogueAction = DialogueAction.ASK_QUESTION
    content: str = ""


class ClarifyingQuestion(BaseModel):
    """Question returned by DialogueService"""

    question_text: str
    question_type: str
    is_final: bool = False  # Is true if the question should end the current phase
    suggested_answers: list[str] | None = None


class QuestionResult(BaseModel):
    """Result from generate_clarifying_question containing the question and extracted context fields"""

    question: ClarifyingQuestion
    extracted_context: dict = {}


class Phase(str, Enum):
    DIRECTION = "direction"
    COLLECTION = "collection"
    PROCESSING = "processing"
    ANALYSIS = "analysis"


class PIRReview(BaseModel):
    """Review result for a single PIR entry"""

    pir_index: int
    approved: bool
    issue: str | None


class ReviewResult(BaseModel):
    """
    Aggregated review of all PIRs from the AI reviewer
    """

    overall_approved: bool
    pir_reviews: list[PIRReview]
    severity: Literal["none", "minor", "major"]
    suggestions: str | None
