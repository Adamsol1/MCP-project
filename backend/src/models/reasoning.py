from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.models.dialogue import ReviewResult

class ReasoningLogEntry(BaseModel):
    session_id: str = Field(..., description = "session id. Uses UUID")
    attempt_number: int = Field(..., ge=1, description="Attempt counter for current session. Starts at one")       # Must be a int
    timestamp: datetime = Field(..., description="Timestamp for attempt")           #Must be a datetime
    generated_pir: str = Field(..., description="Generated PIR content")           #Must be a string
    generation_duration: float = Field(..., ge=0, description="Time spent generating PIR. Uses seconds" )   # Must be a double
    review_result: ReviewResult = Field(..., description="A review result with review information")
    review_duration: float = Field(..., ge=0, description="Time spent reviewing PIR. Uses seconds")   # Must be a double

class UserActionLogEntry(BaseModel):
    session_id: str
    timestamp: datetime
    action: Literal["approve", "reject", "modify"]
    phase: Literal["summary_confirming", "pir_confirming"]
    modifications: str | None = None
