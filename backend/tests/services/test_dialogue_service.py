import pytest

from src.models.dialogue import ClarifyingQuestion, DialogueContext, QuestionResult
from src.services.dialogue_service import DialogueService


class MockLLMService:
    """Mock LLMService that returns pre-configured JSON based on context in prompt."""

    async def generate_json(self, prompt: str) -> dict:
        # Detect which fields are empty from the prompt content
        if '"scope": ""' in prompt or ("MISSING FIELDS" in prompt and "scope" in prompt):
            return {
                "question": "What is the scope of your investigation?",
                "type": "scope",
                "has_sufficient_context": False,
                "context": {"scope": "", "timeframe": "", "target_entities": [], "threat_actors": [], "priority_focus": "", "perspectives": []},
            }
        elif '"timeframe": ""' in prompt:
            return {
                "question": "What time period are you interested in?",
                "type": "timeframe",
                "has_sufficient_context": False,
                "context": {"scope": "recent campaigns", "timeframe": "", "target_entities": [], "threat_actors": [], "priority_focus": "", "perspectives": []},
            }
        else:
            return {
                "question": "I have enough information to proceed.",
                "type": "confirmation",
                "has_sufficient_context": True,
                "context": {"scope": "recent campaigns", "timeframe": "last 6 months", "target_entities": ["Nordic countries"], "threat_actors": ["APT29"], "priority_focus": "TTPs", "perspectives": []},
            }

    async def generate_text(self, prompt: str) -> str:
        return '{"result": "mock", "pirs": [], "reasoning": "mock"}'


class MockAIOrchestrator:
    pass


@pytest.mark.asyncio
async def test_generate_clarifying_question_returns_clarifying_question():
    """Test that generate_clarifying_question returns a QuestionResult."""
    service = DialogueService(MockLLMService(), MockAIOrchestrator())

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


@pytest.mark.asyncio
async def test_generate_clarifying_question_asks_about_scope_when_missing():
    """Test that the service asks about scope when it's not set."""
    service = DialogueService(MockLLMService(), MockAIOrchestrator())

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    # scope is empty → MISSING FIELDS will contain "scope"

    result = await service.generate_clarifying_question(
        user_message="Investigate APT29", context=context
    )

    assert result.question.question_type == "scope"
    assert result.question.is_final is False


@pytest.mark.asyncio
async def test_generate_clarifying_question_asks_about_timeframe_when_scope_set():
    """Test that the service asks about timeframe when scope is set but timeframe is missing."""
    service = DialogueService(MockLLMService(), MockAIOrchestrator())

    context = DialogueContext()
    context.initial_query = "Investigate APT29"
    context.scope = "recent campaigns"
    # timeframe empty → prompt will contain '"timeframe": ""'

    result = await service.generate_clarifying_question(
        user_message="Focus on recent campaigns", context=context
    )

    assert result.question.question_type == "timeframe"
    assert result.question.is_final is False


@pytest.mark.asyncio
async def test_generate_clarifying_question_is_final_when_context_complete():
    """Test that is_final is True when all required context is gathered.

    When all fields are filled, missing_fields is empty, so the backend
    override (force has_sufficient_context=False) does not apply.
    The mock returns has_sufficient_context=True in this case.
    """
    service = DialogueService(MockLLMService(), MockAIOrchestrator())

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
