from fastapi.testclient import TestClient

from src.api import dev_chat
from src.api.main import app


class _FakeProvider:
    name = "local"

    def __init__(self, model: str):
        self.model = model

    async def chat(self, messages):
        return f"echo: {messages[-1]['content']}"


def test_dev_llm_chat_uses_local_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LLM_MODEL", "test-local-model")
    monkeypatch.setattr(
        dev_chat,
        "get_provider",
        lambda model=None: _FakeProvider(model or "test-local-model"),
    )

    response = TestClient(app).post(
        "/api/dev/llm-chat",
        json={
            "messages": [{"role": "user", "content": "ping"}],
            "ai_provider": "local",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "echo: ping",
        "provider": "local",
        "model": "test-local-model",
    }


def test_dev_llm_chat_requires_messages():
    response = TestClient(app).post(
        "/api/dev/llm-chat",
        json={"messages": []},
    )

    assert response.status_code == 422


def test_dev_llm_chat_rejects_invalid_provider():
    response = TestClient(app).post(
        "/api/dev/llm-chat",
        json={
            "messages": [{"role": "user", "content": "ping"}],
            "ai_provider": "not-real",
        },
    )

    assert response.status_code == 400
