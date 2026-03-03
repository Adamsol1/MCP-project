import logging
from typing import Any, cast

from src.models.dialogue import ClarifyingQuestion, DialogueContext, QuestionResult

logger = logging.getLogger("app")


class DialogueService:
    def __init__(self, mcp_client, ai_orchestrator):
        self.mcp_client = mcp_client
        self.ai_orchestrator = ai_orchestrator
        # language is set here as a fallback attribute so the orchestrator path
        # (which calls generate_pir(context) with one arg) still picks up the
        # correct language. dialogue_flow.py sets this before calling the orchestrator.
        self.language: str = "en"

    async def generate_clarifying_question(
        self, user_message: str, context: DialogueContext, language: str = "en"
    ) -> QuestionResult:
        """
        Calls the MCP tool to generate a clarifying question and extract context from the user's answer.

        :param user_message: User message
        :type user_message: str
        :param context: Current dialogue context
        :type context: DialogueContext
        :param language: BCP-47 language code instructing the AI which language to respond in.
        :type language: str
        :return: QuestionResult with question and extracted context fields
        :rtype: QuestionResult
        """
        missing_fields = self._identify_missing_context(context)

        # Include perspectives so the AI can tailor questions to the selected viewpoints
        perspectives = [p.value for p in context.perspectives]

        # Include context to give the tool enough information to ask context based questions instead of general questions.
        question_result = await self.mcp_client.call_tool(
            "dialogue_question",
            {
                "user_message": user_message,
                "missing_fields": missing_fields,
                "perspectives": perspectives,
                "context": {
                    "scope": context.scope,
                    "timeframe": context.timeframe,
                    "target_entities": context.target_entities,
                    "threat_actors": context.threat_actors,
                    "priority_focus": context.priority_focus,
                },
                "language": language,
            },
        )

        # Return question and extracted context separately — let the caller decide what to update
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
    ) -> str:
        """
        Calls the generate_pir MCP tool to create a PIR based on gathered context.

        :param context: The dialogue context with scope, timeframe, target_entities, perspectives
        :type context: DialogueContext
        :param language: BCP-47 language code. Falls back to self.language (set by dialogue_flow
                         before orchestrator calls) when not passed directly.
        :type language: str | None
        :return: The generated PIR as a string
        :rtype: str
        """
        effective_language = language if language is not None else self.language
        perspectives = [p.value for p in context.perspectives]

        result = await self.mcp_client.call_tool(
            "generate_pir",
            {
                "scope": context.scope,
                "timeframe": context.timeframe,
                "target_entities": context.target_entities,
                "perspectives": perspectives,
                "modifications": context.modifications,
                "current_pir": current_pir,
                "threat_actors": context.threat_actors,
                "priority_focus": context.priority_focus,
                "language": effective_language,
            },
        )

        return cast(str, result)

    async def generate_summary(
        self, context: DialogueContext, modifications=None, language: str = "en"
    ) -> dict:
        """
        Calls the generate_summary MCP tool to create a human-readable summary of the context.

        :param context: The dialogue context gathered so far
        :param modifications: Optional user feedback to incorporate
        :param language: BCP-47 language code instructing the AI which language to respond in.
        :type language: str
        :return: Dict with a 'summary' field
        """
        perspectives = [p.value for p in context.perspectives]

        result = await self.mcp_client.call_tool(
            "generate_summary",
            {
                "scope": context.scope,
                "timeframe": context.timeframe,
                "target_entities": context.target_entities,
                "threat_actors": context.threat_actors,
                "priority_focus": context.priority_focus,
                "perspectives": perspectives,
                "modifications": modifications,
                "language": language,
            },
        )

        return cast(dict[Any, Any], result)

    def _identify_missing_context(self, context) -> list[str]:
        """
        Docstring for _identify_missing_context

        :param context: Context from user's dialogue with the AI
        :return: List of missing fields
        :rtype: list[str]
        """
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
