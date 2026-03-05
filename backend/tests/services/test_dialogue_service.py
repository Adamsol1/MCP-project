import json

import pytest

from src.models.dialogue import ClarifyingQuestion, DialogueContext, QuestionResult
from src.services import dialogue_service as dialogue_service_module
from src.services.dialogue_service import DialogueService


class MockMCPClient:
    def __init__(self):
        self.calls = []

    def connect(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ARG002
        return False

    async def get_prompt(self, prompt_name, params):
        self.calls.append({"prompt_name": prompt_name, "params": params})

        if prompt_name != "direction_gathering":
            return "{}"

        missing_fields = json.loads(params["missing_fields"])
        if "scope" in missing_fields:
            return json.dumps(
                {
                    "question": "What is the scope of your investigation?",
                    "type": "scope",
                    "has_sufficient_context": True,
                    "context": {},
                }
            )
        if "timeframe" in missing_fields:
            return json.dumps(
                {
                    "question": "What time period are you interested in?",
                    "type": "timeframe",
                    "has_sufficient_context": True,
                    "context": {},
                }
            )
        if "threat_actors" in missing_fields:
            return json.dumps(
                {
                    "question": "Which threat actors are relevant to your investigation?",
                    "type": "actors",
                    "has_sufficient_context": False,
                    "context": {},
                }
            )

        return json.dumps(
            {
                "question": "I have enough information to proceed.",
                "type": "confirmation",
                "has_sufficient_context": True,
                "context": {},
            }
        )


class MockGeminiAgent:
    def __init__(self, mcp_client):  # noqa: ARG002
        pass

    async def run(self, system_prompt: str, task: str):  # noqa: ARG002
        return system_prompt


class MockAIOrchestrator:
    pass


def _build_service(monkeypatch):
    monkeypatch.setattr(dialogue_service_module, "GeminiAgent", MockGeminiAgent)
    mcp_client = MockMCPClient()
    return DialogueService(mcp_client, MockAIOrchestrator()), mcp_client


@pytest.mark.asyncio
async def test_generate_clarifying_question_returns_clarifying_question(monkeypatch):
    service, mcp_client = _build_service(monkeypatch)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"

    result = await service.generate_clarifying_question(
        user_message="Investigate APT29", context=context
    )

    assert isinstance(result, QuestionResult)
    assert isinstance(result.question, ClarifyingQuestion)
    assert result.question.question_text != ""
    assert result.question.question_type != ""
    assert isinstance(result.extracted_context, dict)
    assert mcp_client.calls[0]["params"]["language"] == "en"


@pytest.mark.asyncio
async def test_generate_clarifying_question_asks_about_scope_when_missing(monkeypatch):
    service, mcp_client = _build_service(monkeypatch)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"

    result = await service.generate_clarifying_question(
        user_message="Investigate APT29", context=context
    )

    assert result.question.question_type == "scope"
    assert result.question.is_final is False
    assert "scope" in json.loads(mcp_client.calls[0]["params"]["missing_fields"])
    assert mcp_client.calls[0]["params"]["language"] == "en"


@pytest.mark.asyncio
async def test_generate_clarifying_question_asks_about_timeframe_when_scope_set(monkeypatch):
    service, mcp_client = _build_service(monkeypatch)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    context.scope = "recent campaigns"

    result = await service.generate_clarifying_question(
        user_message="Focus on recent campaigns", context=context
    )

    assert result.question.question_type == "timeframe"
    assert result.question.is_final is False
    assert "timeframe" in json.loads(mcp_client.calls[0]["params"]["missing_fields"])


@pytest.mark.asyncio
async def test_generate_clarifying_question_asks_about_actors_when_remaining(monkeypatch):
    service, mcp_client = _build_service(monkeypatch)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    context.scope = "recent campaigns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Nordic countries"]

    result = await service.generate_clarifying_question(
        user_message="Focus on known actors", context=context
    )

    assert result.question.question_type == "actors"
    assert result.question.is_final is False
    assert "threat_actors" in json.loads(mcp_client.calls[0]["params"]["missing_fields"])


@pytest.mark.asyncio
async def test_generate_clarifying_question_is_final_when_context_complete(monkeypatch):
    service, mcp_client = _build_service(monkeypatch)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    context.scope = "recent campaigns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Nordic countries"]
    context.threat_actors = ["APT29"]
    context.priority_focus = "TTPs"

    result = await service.generate_clarifying_question(
        user_message="Nordic countries", context=context
    )

    assert result.question.is_final is True
    assert json.loads(mcp_client.calls[0]["params"]["missing_fields"]) == []
