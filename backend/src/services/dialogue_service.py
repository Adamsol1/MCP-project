from src.models.dialogue import ClarifyingQuestion, DialogueContext, QuestionResult


class DialogueService:
    def __init__(self, mcp_client, ai_orchestrator):
        self.mcp_client = mcp_client
        self.ai_orchestrator = ai_orchestrator

    async def generate_clarifying_question(
        self, user_message: str, context: DialogueContext
    ) -> QuestionResult:
        """
        Calls the MCP tool to generate a clarifying question and extract context from the user's answer.

        :param user_message: User message
        :type user_message: str
        :param context: Current dialogue context
        :type context: DialogueContext
        :return: QuestionResult with question and extracted context fields
        :rtype: QuestionResult
        """
        missing_fields = self._identify_missing_context(context)

        # Include perspectives so the AI can tailor questions to the selected viewpoints
        perspectives = [p.value for p in context.perspectives]

        #Include context to give the tool enough information to ask context based questions instead of general questions.
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
                    "threat_actors":context.threat_actors,
                    "priority_focus":context.priority_focus
                }
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

    async def generate_pir(self, context: DialogueContext, modifications=None) -> str:
        """
        Calls the generate_pir MCP tool to create a PIR based on gathered context.

        :param context: The dialogue context with scope, timeframe, target_entities, perspectives
        :type context: DialogueContext
        :param modifications: Optional user feedback for PIR regeneration
        :type modifications: str | None
        :return: The generated PIR as a string
        :rtype: str
        """
        perspectives = [p.value for p in context.perspectives]

        result = await self.mcp_client.call_tool(
            "generate_pir",
            {
                "scope": context.scope,
                "timeframe": context.timeframe,
                "target_entities": context.target_entities,
                "perspectives": perspectives,
                "modifications": modifications,
                "threat_actors":context.threat_actors,
                "priority_focus":context.priority_focus,
            },
        )

        return result

    async def generate_summary(self, context: DialogueContext, modifications=None) -> dict:
        """
        Calls the generate_summary MCP tool to create a human-readable summary of the context.

        :param context: The dialogue context gathered so far
        :param modifications: Optional user feedback to incorporate
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
            },
        )

        return result

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
