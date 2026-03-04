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

        Uses the MCP Resources primitive to pre-fetch relevant knowledge before
        generation (host-driven), in addition to the AI's autonomous tool calls
        (model-driven). This demonstrates both access patterns for RQ1.1.

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
            # MCP Resources primitive: backend pre-fetches relevant knowledge
            # based on context (host-driven), before the AI starts generating.
            background_knowledge = await self._fetch_relevant_resources(context)

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
                    "background_knowledge": background_knowledge,
                },
            )
            # MCP Tools primitive: AI may still call read_knowledge_base()
            # autonomously during the tool-loop to explore additional knowledge.
            agent = GeminiAgent(self.mcp_client)
            raw = await agent.run(
                system_prompt=system_prompt,
                task="Generate Priority Intelligence Requirements (PIRs) based on the provided context.",
            )

        return self._parse_json(raw)

    async def _fetch_relevant_resources(self, context: DialogueContext) -> str:
        """Pre-fetch relevant knowledge using the MCP Resources primitive.

        This is the host-driven counterpart to AI-driven tool calls. The backend
        reads the knowledge index resource, matches resources against the current
        investigation context, and fetches the top matches to inject into the
        PIR generation prompt as grounding knowledge.

        This demonstrates the Resources primitive (RQ1.1): the host decides what
        knowledge is relevant and fetches it proactively, rather than leaving it
        entirely to the AI to discover via tools.

        Args:
            context: Current dialogue context to match knowledge against.

        Returns:
            Formatted background knowledge string, or empty string if no matches.
        """
        try:
            # Step 1: read the index resource to discover available knowledge
            index_json = await self.mcp_client.read_resource("knowledge://index")
            index: list[dict] = json.loads(index_json)
        except Exception as e:
            logger.warning(f"[MCP] Could not read knowledge index resource: {e}")
            return ""

        # Step 2: build a scan text from the investigation context
        scan_parts = [
            context.scope,
            " ".join(context.target_entities),
            " ".join(context.threat_actors or []),
            context.priority_focus or "",
        ]
        scan_text = " ".join(scan_parts).lower()

        if not scan_text.strip():
            return ""

        # Step 3: match resources by keywords, sort by priority
        matches = []
        for entry in index:
            for keyword in entry.get("keywords", []):
                if keyword.lower() in scan_text:
                    matches.append(entry)
                    break
        matches.sort(key=lambda e: e.get("priority", 99))

        if not matches:
            logger.info("[MCP] No matching resources found for current context")
            return ""

        logger.info(
            f"[MCP] Pre-fetching {min(len(matches), 5)} resources via Resources primitive: "
            f"{[m['id'] for m in matches[:5]]}"
        )

        # Step 4: fetch top 5 matching resources
        parts = ["## Background Knowledge (pre-fetched via MCP Resources)"]
        for entry in matches[:5]:
            try:
                content = await self.mcp_client.read_resource(entry["uri"])
                parts.append(f"### Source: {entry['id']}")
                parts.append(content)
            except Exception as e:
                logger.warning(f"[MCP] Failed to read resource {entry['uri']}: {e}")

        return "\n".join(parts) if len(parts) > 1 else ""

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
