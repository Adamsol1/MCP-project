# Tests for reasoning logger - logs AI reasoning during PIR generation


import json
from datetime import datetime
from uuid import uuid4

import pytest

from src.models.dialogue import DialogueContext
from src.models.reasoning import ReasoningLogEntry
from src.services.ai_orchestrator import AIOrchestrator
from src.services.reasoning_logger import ReasoningLogger
from tests.services.conftest import MockGenerator, MockLogger, MockReviewer


# Test for one log
def test_logger_stores_single_attempt():
    # Create a mock log
    log_entry = {
        "session_id": "abc-123",
        "attempt_number": 1,
        "generated_pir": "Fake PIR report",
        "review_approved": True,
    }

    # Initiate logger
    logger = MockLogger()

    # Log the mock data
    logger.create_log(log_entry)

    # Check that it is not empty
    assert logger.logs
    assert logger.logs[0] == log_entry


# Log several logs with same session id
def test_logger_stores_multiple_attempts():
    # Create several logs
    log_entry_1 = {
        "session_id": "abc-123",
        "attempt_number": 1,
        "generated_pir": "Fake PIR report",
        "review_approved": True,
    }
    log_entry_2 = {
        "session_id": "abc-123",
        "attempt_number": 2,
        "generated_pir": "Fake PIR report",
        "review_approved": True,
    }
    log_entry_3 = {
        "session_id": "abc-123",
        "attempt_number": 3,
        "generated_pir": "Fake PIR report",
        "review_approved": True,
    }

    # Initiate logger
    logger = MockLogger()
    # Log all
    logger.create_log(log_entry_1)
    logger.create_log(log_entry_2)
    logger.create_log(log_entry_3)

    # Assert that every log is logged
    assert logger.logs
    assert logger.logs[0] == log_entry_1
    assert logger.logs[1] == log_entry_2
    assert logger.logs[2] == log_entry_3
    assert len(logger.logs) == 3


# Test to log an actual json file
def test_logger_writes_to_jsonl_file(tmp_path):
    session_id = str(uuid4())
    # Create text file
    log_entry = ReasoningLogEntry(
        attempt_number=1,
        timestamp=datetime(2026, 2, 13, 14, 30, 0),
        generated_pir="Fake PIR report",
        generation_duration=0.5,
        is_approved=True,
        review_duration=0.3,
        session_id=session_id
    )

    logger = ReasoningLogger(log_path=tmp_path / "log.jsonl")
    logger.create_log(log_entry)

    saved_log = tmp_path / "log.jsonl"

    assert saved_log.exists()
    assert saved_log.read_text() == json.dumps(log_entry.model_dump(mode="json")) + "\n"


# Test for checking if orchestator logs reasoning
@pytest.mark.asyncio
async def test_orchestrator_logs_reasoning():
    # Lag test context
    context = DialogueContext()
    context.scope = "identify attack patterns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Norway"]

    # Sett opp mocks for test
    generator = MockGenerator()
    # One false and one true. Will mock that first PIR generation is rejected
    reviewer = MockReviewer(responses=[False, True])
    logger = MockLogger()
    orchestrator = AIOrchestrator()

    # Perform generation and pir review with logger
    result = await orchestrator.generate_and_review_pir(
        context, generator, reviewer, logger
    )

    # Check amount of logs saved. Should be two
    assert len(logger.logs) == 2
    # Check that log entries contain timestamp
    assert logger.logs[0].timestamp
    assert logger.logs[1].timestamp
    #Check that all tests get the same id
    assert logger.logs[0].session_id == logger.logs[1].session_id
