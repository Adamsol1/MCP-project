import pytest

from src.models.dialogue import ClarifyingQuestion, DialogueContext, QuestionResult
from src.services.dialogue_service import DialogueService


# Mock MCP client for testing
class MockMCPClient:
    def __init__(self):
        self.calls = []

    async def call_tool(self, tool_name, params):  # noqa: ARG002
        self.calls.append({"tool_name": tool_name, "params": params})
        # Simulate MCP response based on missing context
        missing = params.get("missing_fields", [])
        context = params.get("context", {})
        if "scope" in missing:
            return {
                "question": "What is the scope of your investigation?",
                "type": "scope",
                "has_sufficient_context": False,
                "context": context,
            }
        elif "timeframe" in missing:
            return {
                "question": "What time period are you interested in?",
                "type": "timeframe",
                "has_sufficient_context": False,
                "context": context,
            }
        elif "target_entities" in missing:
            return {
                "question": "Which entities or regions are you focusing on?",
                "type": "target_entities",
                "has_sufficient_context": False,
                "context": context,
            }
        elif "threat_actors" in missing:
            return {
                "question": "Which threat actors are relevant to your investigation?",
                "type": "actors",
                "has_sufficient_context": False,
                "context": context,
            }
        elif "priority_focus" in missing:
            return {
                "question": "What should be the top priority focus?",
                "type": "focus",
                "has_sufficient_context": False,
                "context": context,
            }
        else:
            return {
                "question": "I have enough information to proceed.",
                "type": "confirmation",
                "has_sufficient_context": True,
                "context": context,
            }


# Mock AI orchestrator for testing
class MockAIOrchestrator:
    pass


@pytest.mark.asyncio
async def test_generate_clarifying_question_returns_clarifying_question():
    """Test that generate_clarifying_question returns a ClarifyingQuestion object"""
    mcp_client = MockMCPClient()
    ai_orchestrator = MockAIOrchestrator()
    service = DialogueService(mcp_client, ai_orchestrator)

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
async def test_generate_clarifying_question_asks_about_scope_when_missing():
    """Test that the service asks about scope when it's not set"""
    mcp_client = MockMCPClient()
    ai_orchestrator = MockAIOrchestrator()
    service = DialogueService(mcp_client, ai_orchestrator)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    # scope, timeframe, target_entities are all empty

    result = await service.generate_clarifying_question(
        user_message="Investigate APT29", context=context
    )

    assert result.question.question_type == "scope"
    assert result.question.is_final is False
    assert "scope" in mcp_client.calls[0]["params"]["missing_fields"]
    assert mcp_client.calls[0]["params"]["language"] == "en"


@pytest.mark.asyncio
async def test_generate_clarifying_question_asks_about_timeframe_when_scope_set():
    """Test that the service asks about timeframe when scope is set but timeframe is missing"""
    mcp_client = MockMCPClient()
    ai_orchestrator = MockAIOrchestrator()
    service = DialogueService(mcp_client, ai_orchestrator)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    context.scope = "recent campaigns"
    # timeframe and target_entities still empty

    result = await service.generate_clarifying_question(
        user_message="Focus on recent campaigns", context=context
    )

    assert result.question.question_type == "timeframe"
    assert result.question.is_final is False
    assert "timeframe" in mcp_client.calls[0]["params"]["missing_fields"]


@pytest.mark.asyncio
async def test_generate_clarifying_question_asks_about_actors_when_remaining():
    """Test that the service asks about threat actors when scope/timeframe/targets are set"""
    mcp_client = MockMCPClient()
    ai_orchestrator = MockAIOrchestrator()
    service = DialogueService(mcp_client, ai_orchestrator)

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
    assert "threat_actors" in mcp_client.calls[0]["params"]["missing_fields"]


@pytest.mark.asyncio
async def test_generate_clarifying_question_is_final_when_context_complete():
    """Test that is_final is True when all required context is gathered"""
    mcp_client = MockMCPClient()
    ai_orchestrator = MockAIOrchestrator()
    service = DialogueService(mcp_client, ai_orchestrator)

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    context.scope = "recent campaigns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Nordic countries"]
    context.threat_actors = ["APT29"]
    context.priority_focus = "attack vectors"

    result = await service.generate_clarifying_question(
        user_message="Nordic countries", context=context
    )

    assert result.question.is_final is True
    assert mcp_client.calls[0]["params"]["missing_fields"] == []
