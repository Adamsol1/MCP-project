# Tests for reasoning logger - logs AI reasoning during PIR generation

import json
from datetime import datetime
from uuid import uuid4

import pytest

from src.models.dialogue import DialogueContext
from src.models.reasoning import ReasoningLogEntry
from src.services.ai.ai_orchestrator import AIOrchestrator
from src.services.reasearch_logger import ResearchLogger
from tests.services.conftest import (
    MockGenerator,
    MockLogger,
    MockReviewer,
    make_approved_result,
    make_rejected_result,
)


def test_logger_stores_single_attempt():
    log_entry = {
        "session_id": "abc-123",
        "attempt_number": 1,
        "generated_pir": "Fake PIR report",
        "review_approved": True,
    }

    logger = MockLogger()
    logger.create_log(log_entry)

    assert logger.logs
    assert logger.logs[0] == log_entry


def test_logger_stores_multiple_attempts():
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

    logger = MockLogger()
    logger.create_log(log_entry_1)
    logger.create_log(log_entry_2)
    logger.create_log(log_entry_3)

    assert logger.logs
    assert logger.logs[0] == log_entry_1
    assert logger.logs[1] == log_entry_2
    assert logger.logs[2] == log_entry_3
    assert len(logger.logs) == 3


def test_logger_writes_log_entry_to_db(tmp_path, monkeypatch):
    import sqlite3

    import src.services.reasearch_logger as logger_module

    db_path = tmp_path / "test_sessions.db"
    monkeypatch.setenv("SESSIONS_DB_PATH", str(db_path))
    monkeypatch.setattr(logger_module, "_conn", None)

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS research_log_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, entry_type TEXT, phase TEXT,
            timestamp TEXT, content TEXT
        )"""
    )
    conn.commit()
    conn.close()

    session_id = str(uuid4())
    log_entry = ReasoningLogEntry(
        attempt_number=1,
        timestamp=datetime(2026, 2, 13, 14, 30, 0),
        phase="pir_generation",
        generated_content="Fake PIR report",
        generation_duration=0.5,
        review_result=make_approved_result(),
        review_duration=0.3,
        session_id=session_id,
        model_used="test-model",
    )

    research_logger = ResearchLogger(session_id=session_id)
    research_logger.create_log(log_entry)

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT session_id, phase FROM research_log_entries WHERE session_id = ?",
        (session_id,),
    ).fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0][0] == session_id
    assert rows[0][1] == "pir_generation"


@pytest.mark.asyncio
async def test_orchestrator_logs_reasoning():
    context = DialogueContext()
    context.scope = "identify attack patterns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Norway"]

    generator = MockGenerator()
    reviewer = MockReviewer(responses=[make_rejected_result(), make_approved_result()])
    logger = MockLogger()
    orchestrator = AIOrchestrator(
        research_logger=logger,
        generator_model="test-model",
    )

    result = await orchestrator.generate_and_review_pir(
        context,
        generator,
        reviewer,
        phase="direction",
        session_id="test-session-id",
    )

    assert result == "Generated PIR based on context"
    assert len(logger.logs) == 1
    assert logger.logs[0].attempt_number == 1
    assert logger.logs[0].session_id == "test-session-id"
    assert logger.logs[0].model_used == "test-model"
