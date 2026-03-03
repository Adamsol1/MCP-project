"""ReviewService — AI review for generated content.

All review calls go directly through LLMService (direct Gemini API).
No MCP is involved — the review prompts are backend-side concerns.
"""

import logging

from src.models.dialogue import DialogueContext, ReviewResult
from src.prompts.direction import build_direction_review_prompt
from src.services.llm_service import LLMService

logger = logging.getLogger("app")


class ReviewService:
    """AI review wrapper using LLMService.

    Sends generated content to the AI reviewer and validates
    the response into a ReviewResult model.
    """

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def review_pir(
        self, content, context: DialogueContext, phase: str
    ) -> ReviewResult:
        """Review generated content against the dialogue context.

        Args:
            content: The content to review (str or dict).
            context: The dialogue context used to generate the content.
            phase: Intelligence cycle phase. Valid values: "direction", "collection", "processing".

        Returns:
            ReviewResult with overall_approved, severity, and suggestions.

        Raises:
            KeyError: If phase is not a recognised value.
        """
        logger.info(f"[ReviewService] Reviewing content — phase={phase}")

        prompts = {
            "direction": build_direction_review_prompt,
            # collection and processing prompts added when those phases are built
        }

        if phase not in prompts:
            raise KeyError(f"[ReviewService] Unknown phase: '{phase}'. Valid: {list(prompts)}")

        prompt = prompts[phase](content, context.model_dump())
        result = await self.llm_service.generate_json(prompt)

        response = ReviewResult.model_validate(result)
        logger.info(
            f"[ReviewService] Review result — approved={response.overall_approved}, severity={response.severity}"
        )
        return response
