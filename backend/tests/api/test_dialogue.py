import pytest
from fastapi.testclient import TestClient

from src.api import main
from src.api.main import app
from src.api import dialogue as dialogue_api
from src.models.dialogue import ClarifyingQuestion, PIRReview, QuestionResult, ReviewResult
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
    client = TestClient(app)
    session_id = "test-gather-more-resets"
    session = dialogue_api._get_or_create_session(session_id)
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
    client = TestClient(app)
    session_id = "test-gather-more-no-collection"
    session = dialogue_api._get_or_create_session(session_id)
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
