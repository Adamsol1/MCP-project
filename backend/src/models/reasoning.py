from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.models.dialogue import ReviewResult


class ReasoningLogEntry(BaseModel):
    """
    Logs an AI generation + review result for any phase in the dialogue flow.
    """

    entry_type: Literal["ai_generation"] = "ai_generation"
    session_id: str | None = Field(default=None, description="session id. Uses UUID")
    phase: str = Field(..., description="Dialogue phase, e.g. 'pir_generation', 'collection_planning'")
    attempt_number: int = Field(
        ..., ge=1, description="Attempt counter for current session. Starts at one"
    )
    timestamp: datetime = Field(..., description="Timestamp for attempt")
    generated_content: str = Field(..., description="Generated content for this phase")
    generation_duration: float = Field(
        ..., ge=0, description="Time spent generating content. Uses seconds"
    )
    review_result: ReviewResult | None = Field(
        default=None,
        description="A review result with review information. None if review failed.",
    )
    review_duration: float = Field(
        ..., ge=0, description="Time spent reviewing content. Uses seconds"
    )
    model_used: str = Field(..., description="Model used for AI generation.")
    error_type: str | None = Field(
        default=None,
        description="Exception type if generation or review failed, e.g. 'TimeoutError'",
    )


class UserActionLogEntry(BaseModel):
    """
    Logs a single user action in the dialogue Flow. (approve or reject)
    """

    entry_type: Literal["user_action"] = "user_action"
    session_id: str | None
    timestamp: datetime
    action: Literal["approve", "reject", "modify", "gather_more"]
    phase: str
    modifications: str | None = None
    perspectives_selected: list[str] | None


class ReasoningLog(BaseModel):
    """
    Full AI reasoning trace for a session phase. Written to disk as a single
    JSON file when content is approved by the user.
    """

    session_id: str | None
    phase: str = Field(..., description="Dialogue phase, e.g. 'direction', 'collection'")
    model_used: str
    dialogue_turns: list[dict]
    generated_content_attempts: list = Field(..., description="All generated content attempts before approval")
    review_reasoning: list[dict] = Field(..., description="Review result per generation attempt")
    retry_explanation: list[str]
    final_approved_content: str | None
    timestamps: dict
    retry_triggered: bool = False
    retry_count: int = 0
