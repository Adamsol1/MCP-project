# Test for checking review of PIR

import pytest

from src.models.dialogue import DialogueContext, ReviewResult
from src.services.review_service import ReviewService


class MockReviewMCPClient:
    def __init__(self):
        self.calls = []

    def connect(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ARG002
        return False

    async def get_prompt(self, name, arguments):
        self.calls.append({"name": name, "arguments": arguments})
        return "mock review prompt"


class MockLLMService:
    def __init__(self, return_value):
        self.return_value = return_value
        self.prompts = []

    async def generate_json(self, prompt):
        self.prompts.append(prompt)
        return self.return_value


@pytest.mark.asyncio
async def test_review_pir_is_approved():
    context = DialogueContext()
    context.scope = "identify attack patterns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Norway"]
    fake_pir_report = "Identify attack patterns in Norway over the last 6 months"

    llm = MockLLMService(
        return_value={
            "overall_approved": True,
            "pir_reviews": [{"pir_index": 0, "approved": True, "issue": None}],
            "severity": "none",
            "suggestions": None,
        }
    )
    review_mcp = MockReviewMCPClient()
    review_service = ReviewService(llm, review_mcp)

    result = await review_service.review_pir(fake_pir_report, context, "direction")

    assert isinstance(result, ReviewResult)
    assert result.overall_approved is True
    assert result.severity == "none"
    assert review_mcp.calls[0]["name"] == "direction_review"
    assert llm.prompts[0] == "mock review prompt"


@pytest.mark.asyncio
async def test_review_pir_is_rejected():
    context = DialogueContext()
    context.scope = "identify attack patterns"
    context.timeframe = "last 6 months"
    context.target_entities = ["Norway"]
    faulty_fake_pir_report = "Identify how USA defends against attacks in the last week"

    llm = MockLLMService(
        return_value={
            "overall_approved": False,
            "pir_reviews": [
                {
                    "pir_index": 0,
                    "approved": False,
                    "issue": "Does not meet SMART criteria",
                }
            ],
            "severity": "major",
            "suggestions": "Be more specific",
        }
    )
    review_mcp = MockReviewMCPClient()
    review_service = ReviewService(llm, review_mcp)

    result = await review_service.review_pir(
        faulty_fake_pir_report, context, "direction"
    )

    assert isinstance(result, ReviewResult)
    assert result.overall_approved is False
    assert result.severity == "major"
    assert review_mcp.calls[0]["name"] == "direction_review"
