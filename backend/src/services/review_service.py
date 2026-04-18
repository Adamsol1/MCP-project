"""ReviewService - AI review for generated content via Review MCP Server.

Prompts are fetched from the dedicated review MCP server (port 8002).
The AI call is made via LLMService - no tool loop needed, review is pure synthesis.
"""

import json
import logging
import os

from pydantic import BaseModel

from src.mcp_client.client import MCPClient
from src.models.dialogue import ReviewResult
from src.services.llm_service import LLMService

logger = logging.getLogger("app")


class ReviewService:
    """AI review wrapper using the Review MCP Server for prompts and LLMService for generation.

    Fetches review prompt templates from the dedicated review MCP server (port 8002),
    then calls LLMService (Gemini) to perform the actual review.
    """

    def __init__(self, llm_service: LLMService, review_mcp_client: MCPClient):
        self.llm_service = llm_service
        self.review_mcp_client = review_mcp_client
        # Fail-open by default so review MCP outages do not break the main flow.
        self.fail_open = os.getenv("REVIEW_FAIL_OPEN", "true").lower() == "true"

    def _fallback_result(self, phase: str, exc: Exception) -> ReviewResult:
        reason = (
            f"Review skipped for phase '{phase}' due to reviewer connectivity/runtime issue: "
            f"{type(exc).__name__}"
        )
        logger.warning("[ReviewService] %s", reason)
        return ReviewResult(
            overall_approved=True,
            pir_reviews=[],
            severity="minor",
            suggestions=reason,
        )

    async def review_pir(self, content, context: BaseModel, phase: str) -> ReviewResult:
        """Review generated content against the dialogue context.

        Args:
            content: The content to review (str or dict).
            context: Pydantic BaseModel with phase-specific context fields.
            phase: Intelligence cycle phase. Valid values: "direction", "collection", "processing".

        Returns:
            ReviewResult with overall_approved, severity, and suggestions.

        Raises:
            ValueError: If phase is not a recognized value.
        """
        valid_phases = {"direction", "collection", "processing", "analysis"}
        if phase not in valid_phases:
            raise ValueError(
                f"[ReviewService] Unknown phase: '{phase}'. Valid: {list(valid_phases)}"
            )

        logger.info("[ReviewService] Fetching review prompt for phase=%s", phase)

        try:
            async with self.review_mcp_client.connect():
                prompt = await self.review_mcp_client.get_prompt(
                    f"{phase}_review",
                    {
                        "content": json.dumps(content),
                        "context": json.dumps(context.model_dump()),
                    },
                )

            result = await self.llm_service.generate_json(prompt)
            response = ReviewResult.model_validate(result)
            logger.info(
                "[ReviewService] Review result - approved=%s, severity=%s",
                response.overall_approved,
                response.severity,
            )
            return response
        except Exception as exc:
            logger.exception("[ReviewService] Review execution failed")
            if self.fail_open:
                return self._fallback_result(phase, exc)
            raise
