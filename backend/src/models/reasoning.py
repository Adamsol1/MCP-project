from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.models.dialogue import ReviewResult


class ReasoningLogEntry(BaseModel):
    """
    Logs a AI generation + the review for PIR
    """

    entry_type: Literal["ai_generation"] = "ai_generation"
    session_id: str | None = Field(default=None, description="session id. Uses UUID")
    attempt_number: int = Field(
        ..., ge=1, description="Attempt counter for current session. Starts at one"
    )  # Must be a int
    timestamp: datetime = Field(
        ..., description="Timestamp for attempt"
    )  # Must be a datetime
    generated_pir: str = Field(
        ..., description="Generated PIR content"
    )  # Must be a string
    generation_duration: float = Field(
        ..., ge=0, description="Time spent generating PIR. Uses seconds"
    )  # Must be a double
    review_result: ReviewResult | None = Field(
        default=None,
        description="A review result with review information. None if review failed.",
    )
    review_duration: float = Field(
        ..., ge=0, description="Time spent reviewing PIR. Uses seconds"
    )  # Must be a double
    model_used: str = Field(
        ..., description="Model used for AI generation. e.g Gemini 2.5"
    )
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
    action: Literal["approve", "reject", "modify"]
    phase: Literal["summary_confirming", "pir_confirming"]
    modifications: str | None = None
    perspectives_selected: list[str]


class ReasoningLog(BaseModel):
    """
    Full reasoning for a session. Writes to disk when PIR is approved.

    Logs all PIR generation attempts, review results, and retry history
    """

    session_id: str | None
    model_used: str
    dialogue_turns: list[dict]
    generated_pirs_before_review: list
    review_reasoning_per_pir: list[dict]
    retry_explanation: list[str]
    final_approved_pir: str | None
    timestamps: dict
    retry_triggered: bool = False
    retry_count: int = 0
