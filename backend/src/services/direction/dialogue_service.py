"""DialogueService — Direction phase AI operations via MCP.

Each turn:
  1. Backend fetches the appropriate system prompt from the MCP server (Prompts primitive)
  2. GeminiAgent runs with that system prompt + the user's message
  3. Gemini may autonomously call MCP tools (e.g. read_knowledge_base) during the turn
  4. Backend parses the result and updates state
"""

import json
import logging
import re
from typing import Any

from src.mcp_client.client import MCPClient
from src.models.dialogue import ClarifyingQuestion, DialogueContext, QuestionResult
from src.services.ai.agent_factory import create_tool_agent
from src.services.ai.providers import get_provider

logger = logging.getLogger("app")

JSON_OBJECT_RESPONSE_FORMAT = {"type": "json_object"}


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
            agent = create_tool_agent(self.mcp_client)
            raw = await agent.run(
                system_prompt=system_prompt,
                task=user_message,
                response_format=JSON_OBJECT_RESPONSE_FORMAT,
            )

        question_result = await self._parse_or_repair_json(
            raw=raw,
            repair_prompt=self._clarifying_question_repair_prompt(
                raw=raw,
                user_message=user_message,
                context=context,
                missing_fields=missing_fields,
                language=language,
            ),
            label="clarifying question",
        )

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
            agent = create_tool_agent(self.mcp_client)
            raw = await agent.run(
                system_prompt=system_prompt,
                task="Generate Priority Intelligence Requirements (PIRs) based on the provided context.",
                response_format=JSON_OBJECT_RESPONSE_FORMAT,
            )

        result = await self._parse_or_repair_json(
            raw=raw,
            repair_prompt=self._pir_repair_prompt(
                raw=raw,
                context=context,
                language=effective_language,
            ),
            label="PIR",
        )

        # Gemini 2.5 thinking models put internal reasoning into thought parts
        # and may return an empty "reasoning" field in the JSON. Use the captured
        # thought text as a fallback so the UI can always show reasoning.
        if not result.get("reasoning") and agent.last_thought_text:
            result["reasoning"] = agent.last_thought_text

        # Enrich sources with citation metadata from the knowledge index.
        try:
            async with self.mcp_client.connect():
                index_json = await self.mcp_client.read_resource("knowledge://index")
            index: list[dict] = json.loads(index_json)
            citation_by_id = {
                entry["id"]: entry["citation"]
                for entry in index
                if entry.get("citation")
            }
            for source in result.get("sources", []):
                cit = citation_by_id.get(source.get("id", ""))
                if cit:
                    source["citation"] = cit
        except Exception as e:
            logger.warning(f"[MCP] Source citation enrichment failed: {e}")

        return result

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
            f"[MCP] Pre-fetching {min(len(matches), 8)} resources via Resources primitive: "
            f"{[m['id'] for m in matches[:8]]}"
        )

        # Step 4: fetch top 8 matching resources
        parts = ["## Background Knowledge (pre-fetched via MCP Resources)"]
        for entry in matches[:8]:
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
            agent = create_tool_agent(self.mcp_client)
            raw = await agent.run(
                system_prompt=system_prompt,
                task="Generate a structured summary of the intelligence collection context.",
                response_format=JSON_OBJECT_RESPONSE_FORMAT,
            )

        return self._parse_json(raw)  # type: ignore[no-any-return]

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

    async def _parse_or_repair_json(
        self,
        *,
        raw: str,
        repair_prompt: str,
        label: str,
    ) -> Any:
        try:
            parsed = self._parse_json(raw)
            self._validate_response_shape(parsed, label)
            return parsed
        except ValueError as parse_error:
            logger.warning(
                "[DialogueService] Agent returned unparseable %s JSON; asking model to repair it: %s",
                label,
                parse_error,
            )

        # Bug B fix: route repair through whichever provider is currently
        # active so a Gemini-mode failure doesn't silently cross-fire to the
        # local endpoint (and vice versa).
        repair_client = get_provider()
        repaired = await repair_client.generate_json_text(repair_prompt)
        try:
            parsed = self._parse_json(repaired)
            self._validate_response_shape(parsed, label)
            return parsed
        except ValueError as repair_error:
            raise ValueError(
                f"Agent returned unparseable {label} JSON after repair: {repair_error}"
            ) from repair_error

    @staticmethod
    def _validate_response_shape(parsed: Any, label: str) -> None:
        if not isinstance(parsed, dict):
            raise ValueError(f"{label} response must be a JSON object")

        normalized = label.strip().lower()
        if normalized == "pir":
            # `reasoning` is intentionally not required — Gemini 2.5 thinking
            # models emit it as a thought part and `generate_pir` post-fills
            # it from `agent.last_thought_text`. Forcing it here would push
            # every Gemini response onto the repair path.
            required = {"pir_text", "claims", "sources", "pirs"}
            missing = sorted(required - set(parsed.keys()))
            if missing:
                raise ValueError(
                    f"PIR response missing top-level field(s): {', '.join(missing)}"
                )
            if not isinstance(parsed.get("pirs"), list):
                raise ValueError("PIR response field 'pirs' must be a list")
            return

        if normalized == "clarifying question":
            required = {"question", "type", "has_sufficient_context", "context"}
            missing = sorted(required - set(parsed.keys()))
            if missing:
                raise ValueError(
                    "clarifying question response missing top-level field(s): "
                    + ", ".join(missing)
                )

    @staticmethod
    def _clarifying_question_repair_prompt(
        *,
        raw: str,
        user_message: str,
        context: DialogueContext,
        missing_fields: list[str],
        language: str,
    ) -> str:
        return f"""
Convert the model output below into exactly one valid JSON object for a clarifying question.
Do not invent a completed answer. Preserve any useful question from the model output.

Required shape:
{{
  "question": "one follow-up question written in language {language}",
  "type": "one of: scope, target_entities, threat_actors, timeframe, priority_focus, confirmation",
  "has_sufficient_context": false,
  "context": {{
    "scope": "string",
    "timeframe": "string",
    "target_entities": ["strings"],
    "threat_actors": ["strings"],
    "priority_focus": "string",
    "perspectives": ["strings"]
  }}
}}

Current context JSON:
{context.model_dump_json()}

Missing fields:
{json.dumps(missing_fields)}

User message:
{user_message}

Model output to repair:
{raw}
"""

    @staticmethod
    def _pir_repair_prompt(
        *,
        raw: str,
        context: DialogueContext,
        language: str,
    ) -> str:
        return f"""
Convert the model output below into exactly one valid JSON object for Priority Intelligence Requirements.
Do not replace it with a hardcoded fallback. Preserve the model's PIR content and make only the minimum changes needed for valid JSON.
Write all PIR content in language {language}.

Required shape:
{{
  "pir_text": "string",
  "claims": [
    {{"id": "claim_1", "text": "string", "source_ref": "[1]", "source_id": "source-id"}}
  ],
  "sources": [
    {{"id": "source-id", "ref": "[1]", "source_type": "kb"}}
  ],
  "pirs": [
    {{"question": "string", "priority": "high | medium | low", "rationale": "string", "source_ids": ["source-id"]}}
  ],
  "reasoning": "string"
}}

Use empty arrays for claims and sources if the output has no citations.

Current context JSON:
{context.model_dump_json()}

Model output to repair:
{raw}
"""

    @staticmethod
    def _parse_json(raw: str) -> Any:
        """Parse JSON from raw LLM output, with multiple fallback strategies.

        Handles: bare JSON, markdown code fences, and responses where the model
        prepends prose (e.g. thinking-model preamble) before the JSON block.
        """
        text = raw.strip()
        if not text:
            raise ValueError("Agent returned empty response")

        # 1. Try direct parse (model returned clean JSON)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Strip a leading code fence (```json … ```) and retry
        fence_match = re.search(
            r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE
        )
        if fence_match:
            try:
                return json.loads(fence_match.group(1))
            except json.JSONDecodeError:
                pass

        parsed_candidates: list[Any] = []

        # 3. Extract object starts while allowing trailing text. Some local
        # models emit prose before/after JSON.
        decoder = json.JSONDecoder()
        for match in re.finditer(r"\{", text):
            try:
                parsed, _end = decoder.raw_decode(text[match.start() :])
                parsed_candidates.append(parsed)
            except json.JSONDecodeError:
                continue

        for candidate in DialogueService._json_object_candidates(text):
            for repaired in (
                candidate,
                DialogueService._repair_json_candidate(candidate),
            ):
                try:
                    parsed_candidates.append(json.loads(repaired))
                except json.JSONDecodeError:
                    continue

        selected = DialogueService._select_json_candidate(parsed_candidates)
        if selected is not None:
            return selected

        raise ValueError(f"Could not parse JSON from agent response (length={len(text)})")

    @staticmethod
    def _select_json_candidate(candidates: list[Any]) -> Any | None:
        if not candidates:
            return None

        def score(candidate: Any) -> tuple[int, int]:
            if not isinstance(candidate, dict):
                return (0, 0)
            keys = set(candidate.keys())
            if {"pir_text", "claims", "sources", "pirs"} <= keys:
                return (100, len(keys))
            if {"question", "type", "has_sufficient_context", "context"} <= keys:
                return (90, len(keys))
            if "summary" in keys:
                return (80, len(keys))
            return (10, len(keys))

        return max(candidates, key=score)

    @staticmethod
    def _json_object_candidates(text: str) -> list[str]:
        candidates: list[str] = []
        start: int | None = None
        depth = 0
        in_string = False
        escaped = False

        for index, char in enumerate(text):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                if depth == 0:
                    start = index
                depth += 1
            elif char == "}" and depth:
                depth -= 1
                if depth == 0 and start is not None:
                    candidates.append(text[start : index + 1])
                    start = None

        return candidates

    @staticmethod
    def _repair_json_candidate(text: str) -> str:
        text = re.sub(r"\bNone\b", "null", text)
        text = re.sub(r"\bTrue\b", "true", text)
        text = re.sub(r"\bFalse\b", "false", text)
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        return re.sub(r",\s*([}\]])", r"\1", text)
