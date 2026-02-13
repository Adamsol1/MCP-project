
#Test for checking that values are correctly saved when making a log
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError
import pytest
from src.models.reasoning import ReasoningLogEntry


class TestReasoningLogEntry:
  def test_log_entry_model(self):
    session_id=str(uuid4())
    log_entry = ReasoningLogEntry(
      attempt_number=1,
      timestamp=datetime(2026, 2, 13, 14, 30, 0),
      generated_pir="Test PIR",
      generation_duration=0.5,
      is_approved=True,
      review_duration=0.3,
      session_id=session_id
    )
    assert log_entry.attempt_number == 1
    assert log_entry.is_approved
    assert log_entry.generation_duration == 0.5

  def test_log_entry_rejects_invalid_type(self):
    session_id=str(uuid4())
    with pytest.raises(ValidationError):
        ReasoningLogEntry(
            attempt_number="hei", # type: ignore
            timestamp=datetime(2026, 2, 13, 14, 30, 0),
            generated_pir="Test PIR",
            generation_duration=0.5,
            is_approved=True,
            review_duration=0.3,
            session_id=session_id
        )
