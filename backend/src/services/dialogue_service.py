"""DialogueService — Direction phase AI operations.

All AI calls here go directly through LLMService (direct Gemini API).
No MCP is involved in the Direction phase — this is a deliberate
architectural decision. See plan.md Architectural Design Decisions.
"""

import logging
from typing import Any, cast

from src.models.dialogue import ClarifyingQuestion, DialogueContext, QuestionResult
from src.prompts.direction import (
    build_direction_dialogue_prompt,
    build_pir_generation_prompt,
    build_summary_prompt,
)
from src.services.llm_service import LLMService

logger = logging.getLogger("app")


class DialogueService:
    def __init__(self, llm_service: LLMService, ai_orchestrator):
        self.llm_service = llm_service
        self.ai_orchestrator = ai_orchestrator
        # language is set here as a fallback attribute so the orchestrator path
        # (which calls generate_pir(context) with one arg) still picks up the
        # correct language. dialogue_flow.py sets this before calling the orchestrator.
        self.language: str = "en"

    async def generate_clarifying_question(
        self, user_message: str, context: DialogueContext, language: str = "en"
    ) -> QuestionResult:
        """Generate a clarifying question and extract context from the user's answer.

        Calls LLMService directly — no MCP involved.

        Args:
            user_message: The user's latest message.
            context: Current dialogue context.
            language: BCP-47 language code for the response language.

        Returns:
            QuestionResult with question and extracted context fields.
        """
        missing_fields = self._identify_missing_context(context)
        perspectives = [p.value for p in context.perspectives]

        prompt = build_direction_dialogue_prompt(
            user_message=user_message,
            missing_fields=missing_fields,
            perspectives=perspectives,
            context={
                "scope": context.scope,
                "timeframe": context.timeframe,
                "target_entities": context.target_entities,
                "threat_actors": context.threat_actors,
                "priority_focus": context.priority_focus,
            },
            language=language,
        )

        question_result = await self.llm_service.generate_json(prompt)

        # Backend override: if we know fields are missing, force False regardless of AI judgement
        if missing_fields:
            question_result["has_sufficient_context"] = False

        extracted_context = question_result.get("context", {})
        question = ClarifyingQuestion(
            question_text=question_result["question"],
            question_type=question_result["type"],
            is_final=question_result["has_sufficient_context"],
        )
        return QuestionResult(question=question, extracted_context=extracted_context)

    async def generate_pir(
        self,
        context: DialogueContext,
        language: str | None = None,
        current_pir: str | None = None,
    ) -> Any:
        """Generate PIRs from gathered dialogue context.

        Calls LLMService directly — no MCP involved.

        Args:
            context: The dialogue context with scope, timeframe, target_entities, perspectives.
            language: BCP-47 language code. Falls back to self.language when not passed directly.
            current_pir: Existing PIR string for modification requests.

        Returns:
            The generated PIR as a dict (parsed JSON).
        """
        effective_language = language if language is not None else self.language
        perspectives = [p.value for p in context.perspectives]

        prompt = build_pir_generation_prompt(
            scope=context.scope,
            timeframe=context.timeframe,
            target_entities=context.target_entities,
            perspectives=perspectives,
            threat_actors=context.threat_actors,
            priority_focus=context.priority_focus,
            modifications=context.modifications,
            current_pir=current_pir,
            language=effective_language,
        )

        return await self.llm_service.generate_json(prompt)

    async def generate_summary(
        self, context: DialogueContext, modifications=None, language: str = "en"
    ) -> dict:
        """Generate a human-readable summary of the gathered context.

        Calls LLMService directly — no MCP involved.

        Args:
            context: The dialogue context gathered so far.
            modifications: Optional user feedback to incorporate.
            language: BCP-47 language code for the response language.

        Returns:
            Dict with a 'summary' field.
        """
        perspectives = [p.value for p in context.perspectives]

        prompt = build_summary_prompt(
            scope=context.scope,
            timeframe=context.timeframe,
            target_entities=context.target_entities,
            threat_actors=context.threat_actors,
            priority_focus=context.priority_focus,
            perspectives=perspectives,
            modifications=modifications,
            language=language,
        )

        return cast(dict[str, Any], await self.llm_service.generate_json(prompt))

    def _identify_missing_context(self, context: DialogueContext) -> list[str]:
        """Return a list of context field names that are not yet filled."""
        missing = []
        if not context.scope:
            missing.append("scope")
        if not context.timeframe:
            missing.append("timeframe")
        if not context.target_entities:
            missing.append("target_entities")
        if not context.threat_actors:
            missing.append("threat_actors")
        if not context.priority_focus:
            missing.append("priority_focus")
        return missing
