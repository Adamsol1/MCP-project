from fastapi.testclient import TestClient

from src.api.main import app


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
    assert "type" in data
    assert "is_final" in data
    assert "stage" in data


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
    assert data["sub_state"] == "awaiting_decision"
    assert data["awaiting_user_decision"] is True


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
