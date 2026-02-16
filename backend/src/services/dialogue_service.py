from src.models.dialogue import ClarifyingQuestion, DialogueContext


class DialogueService:
    def __init__(self, mcp_client, ai_orchestrator):
        self.mcp_client = mcp_client
        self.ai_orchestrator = ai_orchestrator

    async def generate_clarifying_question(
        self, user_message: str, context: DialogueContext
    ) -> ClarifyingQuestion:
        """
        Base method for generates claifying questions for collection & planning phase

        :param self: self
        :param user_message: User message
        :type user_message: str
        :param context: Description
        :type context: DialogueContext
        :return: Description
        :rtype: ClarifyingQuestion
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
                }
            },
        )

        # Apply updated context from MCP tool response.
        # The MCP tool analyzes the user's answer and returns updated context values.
        updated_context = question_result.get("context", {})
        if updated_context.get("scope"):
            context.scope = updated_context["scope"]
        if updated_context.get("timeframe"):
            context.timeframe = updated_context["timeframe"]
        if updated_context.get("target_entities"):
            context.target_entities = updated_context["target_entities"]

        return ClarifyingQuestion(
            question_text=question_result["question"],
            question_type=question_result["type"],
            is_final=question_result["has_sufficient_context"],
        )

    #TODO FIKS AT MODIFICATIONS BLIR SENDT MED VIDERE
    async def generate_pir(self, context: DialogueContext, modifications == NONE) -> str:
        """
        Calls the generate_pir MCP tool to create a PIR based on gathered context.

        :param context: The dialogue context with scope, timeframe, target_entities, perspectives
        :type context: DialogueContext
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

        return missing
