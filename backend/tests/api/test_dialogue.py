import pytest
from fastapi.testclient import TestClient

from src.api.main import app


# Test that the endpoint exists and accepts POST requests
def test_dialogue_message_endpoint_exists():
    """Test that POST /api/dialogue/message endpoint exists"""
    client = TestClient(app)

    response = client.post(
        "/api/dialogue/message",
        json={"message": "Investigate APT29", "session_id": "test-session-123"}
    )

    # Should not return 404 (endpoint exists)
    assert response.status_code != 404


def test_dialogue_message_returns_question():
    """Test that the endpoint returns a question structure"""
    client = TestClient(app)

    response = client.post(
        "/api/dialogue/message",
        json={"message": "Investigate APT29", "session_id": "test-session-123"}
    )

    assert response.status_code == 200
    data = response.json()

    # Should have these fields
    assert "question" in data
    assert "type" in data
    assert "is_final" in data


def test_dialogue_message_requires_message_field():
    """Test that message field is required"""
    client = TestClient(app)

    response = client.post(
        "/api/dialogue/message",
        json={"session_id": "test-session-123"}  # Missing message
    )

    assert response.status_code == 422  # Validation error
