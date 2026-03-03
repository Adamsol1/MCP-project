import logging
from pathlib import Path
from typing import Any, cast

from src.models.dialogue import ClarifyingQuestion, DialogueContext, QuestionResult

logger = logging.getLogger("app")


class DialogueService:
    def __init__(
        self,
        mcp_client,
        ai_orchestrator,
        knowledge_service=None,
        knowledge_base_path: str | None = None,
    ):
        self.mcp_client = mcp_client
        self.ai_orchestrator = ai_orchestrator
        self.knowledge_service = knowledge_service
        self.knowledge_base_path = knowledge_base_path
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

        # If knowledge injection is configured, build a scan text from the context and query the knowledge service for relevant resources.
        if self.knowledge_service and self.knowledge_base_path:
            scan_text = self._build_scan_text(context)
            paths = self.knowledge_service.get_relevant_resources(scan_text)
            background_knowledge = self._load_background_knowledge(paths)
        else:
            background_knowledge = None

        tool_params = {
            "scope": context.scope,
            "timeframe": context.timeframe,
            "target_entities": context.target_entities,
            "perspectives": perspectives,
            "modifications": context.modifications,
            "current_pir": current_pir,
            "threat_actors": context.threat_actors,
            "priority_focus": context.priority_focus,
            "language": effective_language,
        }
        if background_knowledge is not None:
            tool_params["background_knowledge"] = background_knowledge

        result = await self.mcp_client.call_tool(
            "generate_pir",
            tool_params,
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

    def _build_scan_text(self, context: DialogueContext) -> str:
        """
        Builds a string from the context to send to the knowledge service for retrieving relevant resources.

        :param context: The dialogue context with scope, timeframe, target_entities, perspectives
        :type context: DialogueContext
        :return: A string representation of the context for scanning
        :rtype: str
        """
        parts = []
        if context.scope:
            parts.append(f"Scope: {context.scope}")
        if context.timeframe:
            parts.append(f"Timeframe: {context.timeframe}")
        if context.target_entities:
            parts.append(f"Target Entities: {', '.join(context.target_entities)}")
        if context.threat_actors:
            parts.append(f"Threat Actors: {', '.join(context.threat_actors)}")
        if context.priority_focus:
            parts.append(f"Priority Focus: {context.priority_focus}")
        if context.perspectives:
            perspectives_str = ", ".join(p.value for p in context.perspectives)
            parts.append(f"Perspectives: {perspectives_str}")

        logging.debug("DialogueService: Built scan text for knowledge retrieval: %s", parts)
        return "\n".join(parts)

    def _load_background_knowledge(self, paths: list[str]) -> str | None:
        """
        Loads background knowledge from a set of file to include in the MCP call. With links to each sources so the AI can attribute information correctly.

        :param paths: List of paths to the knowledge files
        :type paths: list[str]
        :return: The combined content of the knowledge files as a string
        :rtype: str | None
        """
        if not self.knowledge_base_path:
            return None

        content = [
            "## Background Knowledge"
        ]  # Header for the MCP prompt template to recognize this section

        for path in paths:
            try:
                full_path = Path(self.knowledge_base_path) / path
                file_content = full_path.read_text(encoding="utf-8")
                # Only reach here if file exists — safe to append both
                content.append(f"### Source: {path}")
                content.append(file_content)
            except FileNotFoundError:
                continue

        if len(content) == 1:
            logging.info("DialogueService: No valid knowledge files found for paths: %s", paths)
            return None  # No valid knowledge loaded, return none instead of just the header

        logging.info("DialogueService: Loaded background knowledge from paths: %s", paths)
        return "\n".join(content)
