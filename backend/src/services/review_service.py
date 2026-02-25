"""Service for reviewing generated PIRs using the MCP review tool."""

import logging

from src.models.dialogue import DialogueContext, ReviewResult

logger = logging.getLogger("app")


class ReviewService:
    """Wrapper around the MCP review tool.

    Sends generated PIRs to the AI reviewer and validates
    the response into a ReviewResult model.
    """

    def __init__(self, mcp_client):
        """Initialize ReviewService.

        Args:
            mcp_client: A connected MCPClient instance.
        """
        self.mcp_client = mcp_client

    async def review_pir(
        self, content, context: DialogueContext, phase: str
    ) -> ReviewResult:
        """Review a generated PIR against the dialogue context.

        Args:
            content: The PIR content to review (str or dict).
            context: The dialogue context used to generate the PIR.
            phase: Intelligence cycle phase. Valid values: "direction", "collection", "processing".

        Returns:
            ReviewResult with overall_approved, severity ("none" | "minor" | "major"), and suggestions.

        Raises:
            KeyError: If phase is not a valid value.
        """
        logger.info(f"[ReviewService] Reviewing PIR — phase={phase}")
        # Call AI service to review PIR against context
        result = await self.mcp_client.call_tool(
            "review",
            {"content": content, "context": context.model_dump(), "phase": phase},
        )

        response = ReviewResult.model_validate(result)
        logger.info(
            f"[ReviewService] Review result — approved={response.overall_approved}, severity={response.severity}"
        )
        return response
