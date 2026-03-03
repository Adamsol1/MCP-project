# Test for checking that values are correctly saved when making a log
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.dialogue import PIRReview, ReviewResult
from src.models.reasoning import ReasoningLogEntry


def _make_approved_result():
    return ReviewResult(
        overall_approved=True,
        pir_reviews=[PIRReview(pir_index=0, approved=True, issue=None)],
        severity="none",
        suggestions=None,
    )


class TestReasoningLogEntry:
    def test_log_entry_model(self):
        session_id = str(uuid4())
        log_entry = ReasoningLogEntry(
            attempt_number=1,
            timestamp=datetime(2026, 2, 13, 14, 30, 0),
            phase="pir_generation",
            generated_content="Test PIR",
            generation_duration=0.5,
            review_result=_make_approved_result(),
            review_duration=0.3,
            session_id=session_id,
            model_used="test-model",
        )
        assert log_entry.attempt_number == 1
        assert log_entry.review_result.overall_approved
        assert log_entry.generation_duration == 0.5

    def test_log_entry_rejects_invalid_type(self):
        session_id = str(uuid4())
        with pytest.raises(ValidationError):
            ReasoningLogEntry(
                attempt_number="hei",  # type: ignore
                timestamp=datetime(2026, 2, 13, 14, 30, 0),
                phase="pir_generation",
                generated_content="Test PIR",
                generation_duration=0.5,
                review_result=_make_approved_result(),
                review_duration=0.3,
                session_id=session_id,
                model_used="test-model",
            )
