
#Test for checking review of PIR

import pytest

from src.models.dialogue import DialogueContext, ReviewResult
from src.services.review_service import ReviewService


# Mock MCP client. Will simulate MCP tool answer
# return_value er en dict som matcher ReviewResult-strukturen
class MockMCPClient:
  def __init__(self, return_value):
    self.return_value = return_value

  async def call_tool(self, tool_name, arguments):  # noqa: ARG002
    return self.return_value


@pytest.mark.asyncio
async def test_review_pir_is_approved():
  #Create enviorment for test
  context = DialogueContext()
  context.scope = "identify attack patterns"
  context.timeframe = "last 6 months"
  context.target_entities = ["Norway"]
  fake_pir_report = "Identify attack patterns in Norway over the last 6 months"

  # Mock MCP client som returnerer godkjent resultat
  mock_client = MockMCPClient(return_value={
    "overall_approved": True,
    "pir_reviews": [{"pir_index": 0, "approved": True, "issue": None}],
    "severity": "none",
    "suggestions": None,
  })
  review_service = ReviewService(mock_client)

  #Perform method call
  result = await review_service.review_pir(fake_pir_report, context, "direction")

  #Check results
  assert isinstance(result, ReviewResult)
  assert result.overall_approved is True
  assert result.severity == "none"


@pytest.mark.asyncio
async def test_review_pir_is_rejected():
  #Create enviorment for test
  context = DialogueContext()
  context.scope = "identify attack patterns"
  context.timeframe = "last 6 months"
  context.target_entities = ["Norway"]
  faulty_fake_pir_report = "Identify how USA defends against attacks in the last week"

  # Mock MCP client som returnerer avvist resultat
  mock_client = MockMCPClient(return_value={
    "overall_approved": False,
    "pir_reviews": [{"pir_index": 0, "approved": False, "issue": "Does not meet SMART criteria"}],
    "severity": "major",
    "suggestions": "Be more specific",
  })
  review_service = ReviewService(mock_client)

  #Perform method call
  result = await review_service.review_pir(faulty_fake_pir_report, context, "direction")

  #Check results
  assert isinstance(result, ReviewResult)
  assert result.overall_approved is False
  assert result.severity == "major"
