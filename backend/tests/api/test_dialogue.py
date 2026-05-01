import asyncio
import sqlite3
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from src.api import dialogue as dialogue_api
from src.api import main
from src.api.main import app
from src.db import engine as db_engine
from src.db.models.session_tables import SessionTable  # noqa: F401  (registers table)
from src.models.dialogue import (
    ClarifyingQuestion,
    PIRReview,
    QuestionResult,
    ReviewResult,
)
from src.services.state_machines.collection_flow import CollectionFlow, CollectionState
from src.services.state_machines.processing_flow import ProcessingFlow


class _FakeDialogueService:
    def __init__(self, *args, **kwargs):  # noqa: ARG002
        self.language = "en"

    async def generate_clarifying_question(self, user_message, context, language="en"):  # noqa: ARG002
        question = ClarifyingQuestion(
            question_text="What is your scope?",
            question_type="scope",
            is_final=False,
        )
        return QuestionResult(question=question, extracted_context={})

    async def generate_pir(self, context, language=None, current_pir=None):  # noqa: ARG002
        return {"result": "Mock PIR", "pirs": [], "reasoning": "Mock"}

    async def generate_summary(self, context, modifications=None, language="en"):  # noqa: ARG002
        return {"summary": "Mock summary"}


class _FakeReviewService:
    def __init__(self, *args, **kwargs):  # noqa: ARG002
        pass

    async def review_pir(self, content, context, phase):  # noqa: ARG002
        return ReviewResult(
            overall_approved=True,
            pir_reviews=[PIRReview(pir_index=0, approved=True, issue=None)],
            severity="none",
            suggestions=None,
        )


@pytest.fixture(autouse=True)
def _mock_api_dependencies(monkeypatch):
    dialogue_api._sessions.clear()
    monkeypatch.setattr(dialogue_api, "DialogueService", _FakeDialogueService)
    monkeypatch.setattr(dialogue_api, "ReviewService", _FakeReviewService)
    monkeypatch.setattr(dialogue_api, "DEV_TOOLS_ENABLED", True)


# Test that the endpoint exists and accepts POST requests
def test_dialogue_message_endpoint_exists():
    """Test that POST /api/dialogue/message endpoint exists"""
    client = TestClient(app)

    response = client.post(
        "/api/dialogue/message",
        json={"message": "Investigate APT29", "session_id": "test-session-123"},
    )

    # Should not return 404 (endpoint exists)
    assert response.status_code != 404


def test_dialogue_message_returns_question():
    """Test that the endpoint returns a question structure"""
    client = TestClient(app)

    response = client.post(
        "/api/dialogue/message",
        json={"message": "Investigate APT29", "session_id": "test-session-123"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should have these fields
    assert "question" in data
    assert "action" in data
    assert "stage" in data
    assert "phase" in data
    assert "type" not in data
    assert "is_final" not in data


def test_dialogue_message_requires_message_field():
    """Test that message field is required"""
    client = TestClient(app)

    response = client.post(
        "/api/dialogue/message",
        json={"session_id": "test-session-123"},  # Missing message
    )

    assert response.status_code == 422  # Validation error


def test_dev_state_endpoint_returns_stage_snapshot():
    client = TestClient(app)
    session_id = "dev-session-state-1"

    response = client.get("/api/dialogue/dev/state", params={"session_id": session_id})
    assert response.status_code == 200

    data = response.json()
    assert data["session_id"] == session_id
    assert data["stage"] == "initial"
    assert data["phase"] == "direction"
    assert "missing_context_fields" in data


def test_dev_state_can_force_stage():
    client = TestClient(app)
    session_id = "dev-session-state-2"

    response = client.post(
        "/api/dialogue/dev/state",
        json={
            "session_id": session_id,
            "stage": "summary_confirming",
            "sub_state": "awaiting_decision",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "summary_confirming"
    assert data["phase"] == "direction"
    assert data["sub_state"] == "awaiting_decision"
    assert data["awaiting_user_decision"] is True


def test_gather_more_resets_processing_to_collection():
    """gather_more=True during processing phase should reset back to collection."""
    # Arrange
    from src.api.dialogue import IntelligenceSession
    from src.services.reasearch_logger import ResearchLogger

    client = TestClient(app)
    session_id = "test-gather-more-resets"
    session = IntelligenceSession(session_id, ResearchLogger(session_id))
    dialogue_api._sessions[session_id] = session
    session.collection_flow = CollectionFlow(session_id=session_id)
    session.processing_flow = ProcessingFlow(session_id=session_id)

    # Act
    response = client.post(
        "/api/dialogue/message",
        json={"message": "", "session_id": session_id, "gather_more": True},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["action"] == "select_gaps"
    assert session.processing_flow is None
    assert session.collection_flow.state == CollectionState.REVIEWING


def test_gather_more_without_collection_flow_returns_400():
    """gather_more=True with no collection flow should return 400."""
    # Arrange
    from src.api.dialogue import IntelligenceSession
    from src.services.reasearch_logger import ResearchLogger

    client = TestClient(app)
    session_id = "test-gather-more-no-collection"
    session = IntelligenceSession(session_id, ResearchLogger(session_id))
    dialogue_api._sessions[session_id] = session
    session.processing_flow = ProcessingFlow(session_id=session_id)
    session.collection_flow = None

    # Act
    response = client.post(
        "/api/dialogue/message",
        json={"message": "", "session_id": session_id, "gather_more": True},
    )

    # Assert
    assert response.status_code == 400


def test_dev_set_state_with_invalid_stage_returns_400():
    # Arrange
    client = TestClient(app)

    # Act
    response = client.post(
        "/api/dialogue/dev/state",
        json={"session_id": "dev-invalid-stage", "stage": "not_a_real_stage"},
    )

    # Assert
    assert response.status_code == 400
    assert "not_a_real_stage" in response.json()["detail"]


def test_get_collection_status_returns_404_when_no_status():
    # Arrange
    client = TestClient(app)

    # Act
    response = client.get("/api/dialogue/collection-status/nonexistent-session-id")

    # Assert
    assert response.status_code == 404


@pytest.fixture
def mock_upload_path(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_ROOT", tmp_path)
    return tmp_path


def test_health_returns_200():
    # Arrange
    client = TestClient(app)

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_delete_session_returns_204(mock_upload_path):  # noqa: ARG001
    # Arrange
    client = TestClient(app)

    # Act
    response = client.delete("/api/sessions/test-delete-session")

    # Assert
    assert response.status_code == 204


def test_delete_nonexistent_session_returns_204(mock_upload_path):  # noqa: ARG001
    # Arrange
    client = TestClient(app)

    # Act
    response = client.delete("/api/sessions/does-not-exist")

    # Assert
    assert response.status_code == 204


@pytest.fixture
def _temp_sessions_db(monkeypatch, tmp_path):
    """Point the sessions engine at a fresh sqlite file and init its schema."""
    db_path = tmp_path / "sessions.db"
    monkeypatch.setenv("SESSIONS_DB_PATH", str(db_path))
    # Reset the engine/session-factory singletons so they pick up the new path
    monkeypatch.setattr(db_engine, "_sessions_engine", None)
    monkeypatch.setattr(db_engine, "_sessions_session_factory", None)

    async def _init_schema():
        engine = db_engine.get_sessions_engine()
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    asyncio.run(_init_schema())
    try:
        yield db_path
    finally:
        # Drop singletons so other tests get a fresh engine pointed at the
        # default DB path once the env var is un-set by monkeypatch.
        monkeypatch.setattr(db_engine, "_sessions_engine", None, raising=False)
        monkeypatch.setattr(
            db_engine, "_sessions_session_factory", None, raising=False
        )


def _insert_session_row(db_path, session_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO sessions (id, created_at, updated_at, direction_state, "
        "question_count) VALUES (?, ?, ?, 'initial', 0)",
        (session_id, now, now),
    )
    conn.execute(
        "INSERT INTO collection_attempts "
        "(session_id, attempt_number, pir, raw_response, created_at) "
        "VALUES (?, 1, '', '', ?)",
        (session_id, now),
    )
    conn.commit()
    conn.close()


def _count_session_rows(db_path, session_id: str) -> tuple[int, int]:
    conn = sqlite3.connect(str(db_path))
    sessions = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()[0]
    children = conn.execute(
        "SELECT COUNT(*) FROM collection_attempts WHERE session_id = ?",
        (session_id,),
    ).fetchone()[0]
    conn.close()
    return sessions, children


def test_delete_session_removes_row_and_children(
    mock_upload_path, _temp_sessions_db
):  # noqa: ARG001
    """DELETE must actually remove the session row and child rows from the DB."""
    session_id = "delete-me-123"
    _insert_session_row(_temp_sessions_db, session_id)
    dialogue_api._deleted_sessions.discard(session_id)

    assert _count_session_rows(_temp_sessions_db, session_id) == (1, 1)

    client = TestClient(app)
    response = client.delete(f"/api/sessions/{session_id}")

    assert response.status_code == 204
    assert _count_session_rows(_temp_sessions_db, session_id) == (0, 0)


def test_deleted_session_cannot_be_resurrected_by_in_flight_save(
    mock_upload_path, _temp_sessions_db
):  # noqa: ARG001
    """After DELETE, a concurrent _save_session must not re-insert the row.

    Simulates the race where a long-running /api/dialogue/message handler holds
    a reference to an IntelligenceSession object that pre-dates the DELETE and
    tries to upsert it back into the DB when it finishes.
    """
    session_id = "race-target-456"
    dialogue_api._deleted_sessions.discard(session_id)

    # Seed the session in the DB, then delete it via the API
    _insert_session_row(_temp_sessions_db, session_id)
    client = TestClient(app)
    assert client.delete(f"/api/sessions/{session_id}").status_code == 204
    assert _count_session_rows(_temp_sessions_db, session_id) == (0, 0)

    # Simulate the in-flight handler completing after the delete: build a
    # stale IntelligenceSession and try to save it.
    from src.api.dialogue import IntelligenceSession, _save_session
    from src.db.unit_of_work import UnitOfWork
    from src.services.reasearch_logger import ResearchLogger

    async def _attempt_resave():
        session = IntelligenceSession(session_id, ResearchLogger(session_id))
        factory = db_engine.get_sessions_session_factory()
        async with factory() as db_session:
            uow = UnitOfWork(db_session)
            await _save_session(session, uow)

    asyncio.run(_attempt_resave())

    # Row must still be gone — tombstone blocks the resurrection
    assert _count_session_rows(_temp_sessions_db, session_id) == (0, 0)


def test_dev_reset_sets_stage_initial():
    client = TestClient(app)
    session_id = "dev-session-state-3"

    client.post(
        "/api/dialogue/dev/state",
        json={
            "session_id": session_id,
            "stage": "pir_confirming",
            "sub_state": "awaiting_decision",
        },
    )
    reset_response = client.post(
        "/api/dialogue/dev/reset", params={"session_id": session_id}
    )
    assert reset_response.status_code == 200
    data = reset_response.json()
    assert data["stage"] == "initial"
    assert data["phase"] == "direction"
