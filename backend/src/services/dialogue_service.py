"""DialogueService — Direction phase AI operations via MCP.

Each turn:
  1. Backend fetches the appropriate system prompt from the MCP server (Prompts primitive)
  2. GeminiAgent runs with that system prompt + the user's message
  3. Gemini may autonomously call MCP tools (e.g. read_knowledge_base) during the turn
  4. Backend parses the result and updates state
"""

import json
import logging
from typing import Any

from src.mcp_client.client import MCPClient
from src.models.dialogue import ClarifyingQuestion, DialogueContext, QuestionResult
from src.services.gemini_agent import GeminiAgent

logger = logging.getLogger("app")


class DialogueService:
    def __init__(self, mcp_client: MCPClient, ai_orchestrator):
        self.mcp_client = mcp_client
        self.ai_orchestrator = ai_orchestrator
        # language is set here as a fallback attribute so the orchestrator path
        # (which calls generate_pir(context) with one arg) still picks up the
        # correct language. dialogue_flow.py sets this before calling the orchestrator.
        self.language: str = "en"

    async def generate_clarifying_question(
        self, user_message: str, context: DialogueContext, language: str = "en"
    ) -> QuestionResult:
        """Generate a clarifying question and extract context from the user's answer.

        Fetches the direction_gathering system prompt from the MCP server, then
        runs GeminiAgent so Gemini can optionally call knowledge bank tools.

        Args:
            user_message: The user's latest message.
            context: Current dialogue context.
            language: BCP-47 language code for the response language.

        Returns:
            QuestionResult with question and extracted context fields.
        """
        missing_fields = self._identify_missing_context(context)

        async with self.mcp_client.connect():
            system_prompt = await self.mcp_client.get_prompt(
                "direction_gathering",
                {
                    "user_message": user_message,
                    "missing_fields": json.dumps(missing_fields),
                    "context": context.model_dump_json(),
                    "language": language,
                },
            )
            agent = GeminiAgent(self.mcp_client)
            raw = await agent.run(system_prompt=system_prompt, task=user_message)

        question_result = self._parse_json(raw)

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

        Args:
            context: The dialogue context with scope, timeframe, target_entities, perspectives.
            language: BCP-47 language code. Falls back to self.language when not passed directly.
            current_pir: Existing PIR string for modification requests.

        Returns:
            The generated PIR as a dict (parsed JSON).
        """
        effective_language = language if language is not None else self.language
        perspectives = [p.value for p in context.perspectives]

        async with self.mcp_client.connect():
            system_prompt = await self.mcp_client.get_prompt(
                "direction_pir",
                {
                    "scope": context.scope,
                    "timeframe": context.timeframe,
                    "target_entities": json.dumps(context.target_entities),
                    "threat_actors": json.dumps(context.threat_actors or []),
                    "priority_focus": context.priority_focus or "",
                    "perspectives": json.dumps(perspectives),
                    "modifications": context.modifications or "",
                    "current_pir": current_pir or "",
                    "language": effective_language,
                },
            )
            agent = GeminiAgent(self.mcp_client)
            raw = await agent.run(
                system_prompt=system_prompt,
                task="Generate Priority Intelligence Requirements (PIRs) based on the provided context.",
            )

        return self._parse_json(raw)

    async def generate_summary(
        self, context: DialogueContext, modifications=None, language: str = "en"
    ) -> dict:
        """Generate a human-readable summary of the gathered context.

        Args:
            context: The dialogue context gathered so far.
            modifications: Optional user feedback to incorporate.
            language: BCP-47 language code for the response language.

        Returns:
            Dict with a 'summary' field.
        """
        perspectives = [p.value for p in context.perspectives]

        async with self.mcp_client.connect():
            system_prompt = await self.mcp_client.get_prompt(
                "direction_summary",
                {
                    "scope": context.scope,
                    "timeframe": context.timeframe,
                    "target_entities": json.dumps(context.target_entities),
                    "threat_actors": json.dumps(context.threat_actors or []),
                    "priority_focus": context.priority_focus or "",
                    "perspectives": json.dumps(perspectives),
                    "modifications": modifications or "",
                    "language": language,
                },
            )
            agent = GeminiAgent(self.mcp_client)
            raw = await agent.run(
                system_prompt=system_prompt,
                task="Generate a structured summary of the intelligence collection context.",
            )

        return self._parse_json(raw)

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

    @staticmethod
    def _parse_json(raw: str) -> Any:
        """Parse JSON from raw LLM output, stripping markdown code fences if present."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1])
        return json.loads(text)
