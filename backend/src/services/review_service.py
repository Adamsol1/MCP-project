
from src.models.dialogue import DialogueContext, ReviewResult


class ReviewService:
  #Review service for PIR reports
  def __init__(self, mcp_client):
    self.mcp_client = mcp_client

  async def review_pir(self, content, context: DialogueContext, phase):
    #Call AI service to review PIR against context
    result = await self.mcp_client.call_tool("review", {"content":content, "context":context.model_dump(), "phase":phase})

    response = ReviewResult.model_validate(result)

    return response
