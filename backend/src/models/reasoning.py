from datetime import datetime

from pydantic import BaseModel, Field


#TODO : update to include review feedback when implemented
class ReasoningLogEntry(BaseModel):
    session_id: str = Field(..., description = "session id. Uses UUID")
    attempt_number: int = Field(..., ge=1, description="Attempt counter for current session. Starts at one")       # Must be a int
    timestamp: datetime = Field(..., description="Timestamp for attempt")           #Must be a datetime
    generated_pir: str = Field(..., description="Generated PIR content")           #Must be a string
    generation_duration: float = Field(..., ge=0, description="Time spent generating PIR. Uses seconds" )   # Must be a double
    is_approved: bool = Field(..., description="Bool for if the attempt was approved or not")            # Must be true/false
    review_duration: float = Field(..., ge=0, description="Time spent reviewing PIR. Uses seconds")   # Must be a double
