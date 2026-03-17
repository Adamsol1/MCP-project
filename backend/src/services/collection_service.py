"""CollectionService

For each collection phase we:
1. Backend fetches the system prompt from MCP server and sends it to a Gemini agent.
2. Gemini agent executes prompts and uses allowed tools.
3. Agent returns collected/derived content.
4. Backend returns structured content to CollectionFlow for frontend review.
"""

import json
import logging
import re
from typing import Any

from src.mcp_client.client import MCPClient
from src.services.gemini_agent import GeminiAgent

logger = logging.getLogger("app")

_DEFAULT_SOURCE = "Internal Knowledge Bank"
# Substring rules for noisy model outputs: all tokens in a tuple must appear
# in the lowercased source string for the rule to fire (AND within a tuple,
# first match wins across the list).
_SUBSTRING_RULES: list[tuple[tuple[str, ...], str]] = [
    (("otx",),               "AlienVault OTX"),
    (("alienvault",),        "AlienVault OTX"),
    (("knowledge", "bank"),  "Internal Knowledge Bank"),
    (("misp",),              "MISP"),
    (("upload",),            "Uploaded Documents"),
    (("local document",),    "Uploaded Documents"),
    (("web",),               "Web Search"),
    (("duckduckgo",),        "Web Search"),
    (("fetch",),             "Web Search"),
]

_SOURCE_ALIASES = {
    "internal knowledge bank": "Internal Knowledge Bank",
    "knowledge bank": "Internal Knowledge Bank",
    "local knowledge bank": "Internal Knowledge Bank",
    "otx": "AlienVault OTX",
    "alienvault": "AlienVault OTX",
    "alienvault otx": "AlienVault OTX",
    "misp": "MISP",
    "uploaded documents": "Uploaded Documents",
    "user uploads": "Uploaded Documents",
    "uploads": "Uploaded Documents",
    "local documents": "Uploaded Documents",
    "web search": "Web Search",
    "web_search": "Web Search",
    "web fetch": "Web Search",
    "web_fetch": "Web Search",
    "duckduckgo": "Web Search",
}

TOOL_TO_DISPLAY_NAME: dict[str, str] = {
    "list_knowledge_base": "Internal Knowledge Bank",
    "read_knowledge_base": "Internal Knowledge Bank",
    "query_otx": "AlienVault OTX",
    "search_local_data": "Uploaded Documents",
    "list_uploads": "Uploaded Documents",
    "read_upload": "Uploaded Documents",
    "web_search": "Web Search",
    "fetch_page": "Web Search",
}


class CollectionService:

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        """Parse a JSON object from text, tolerating markdown code fences and wrappers."""
        if not isinstance(text, str):
            return None

        stripped = text.strip()
        if not stripped:
            return None

        # 1) direct JSON
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # 2) fenced blocks (```json ... ``` or ``` ... ```)
        for candidate in re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, flags=re.IGNORECASE):
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue

        # 3) largest object-like substring
        start = stripped.find("{")
        end = stripped.rfind("}")
        if 0 <= start < end:
            snippet = stripped[start : end + 1]
            try:
                parsed = json.loads(snippet)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return None

        return None

    @staticmethod
    def _normalize_source_name(raw: str) -> str | None:
        if not isinstance(raw, str):
            return None
        normalized = raw.strip()
        if not normalized:
            return None

        key = normalized.lower()
        if key in _SOURCE_ALIASES:
            return _SOURCE_ALIASES[key]

        # Alias-by-substring to catch noisy model outputs
        for tokens, canonical in _SUBSTRING_RULES:
            if all(token in key for token in tokens):
                return canonical

        return normalized

    @classmethod
    def _normalize_sources(cls, raw_sources: Any) -> list[str]:
        if not isinstance(raw_sources, list):
            return []

        deduped: list[str] = []
        for source in raw_sources:
            normalized = cls._normalize_source_name(source)
            if normalized and normalized not in deduped:
                deduped.append(normalized)
        return deduped

    @staticmethod
    def _try_parse_json_lenient(s: str) -> dict | None:
        """Try json.loads; on failure strip trailing commas and retry once."""
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        try:
            repaired = re.sub(r",\s*([}\]])", r"\1", s)
            return json.loads(repaired)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def parse_collected_data(raw_data: str) -> dict[str, Any]:
        """Parse raw collected_data JSON into a structured display payload.

        Returns a dict with:
          - collected_data: the original list of {source, resource_id, content} items
          - source_summary: per-source aggregates [{display_name, count, resource_ids, has_content}]
        On parse failure returns {collected_data: [], source_summary: [], parse_error: raw_data}.
        Never throws.
        """
        try:
            stripped = raw_data.strip() if isinstance(raw_data, str) else ""
            fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, re.IGNORECASE)
            if fence_match:
                stripped = fence_match.group(1).strip()
            parsed = CollectionService._try_parse_json_lenient(stripped) if stripped else {}
            if parsed is None:
                raise json.JSONDecodeError("Could not repair JSON", stripped, 0)
            items: list[dict] = parsed.get("collected_data", [])
            if not isinstance(items, list):
                raise ValueError("collected_data is not a list")

            # Build per-source aggregates
            stats: dict[str, dict] = {}
            for item in items:
                tool_name: str = str(item.get("source") or "unknown")
                display_name: str = TOOL_TO_DISPLAY_NAME.get(tool_name, tool_name)
                if display_name not in stats:
                    stats[display_name] = {"count": 0, "resource_ids": [], "has_content": False}
                stats[display_name]["count"] += 1
                rid = item.get("resource_id")
                if rid and rid not in stats[display_name]["resource_ids"]:
                    stats[display_name]["resource_ids"].append(rid)
                content = item.get("content", "")
                if content and content.strip():
                    stats[display_name]["has_content"] = True

            source_summary = [
                {
                    "display_name": name,
                    "count": s["count"],
                    "resource_ids": s["resource_ids"],
                    "has_content": s["has_content"],
                }
                for name, s in sorted(stats.items())
            ]

            return {"collected_data": items, "source_summary": source_summary}

        except Exception:
            logger.exception("[CollectionService] Failed to parse collected_data")
            return {"collected_data": [], "source_summary": [], "parse_error": raw_data}

    @classmethod
    def _coerce_plan_payload(cls, raw_plan: str) -> dict[str, Any]:
        """Return a stable payload with at least {plan, suggested_sources}."""
        parsed = cls._try_parse_json(raw_plan)
        if parsed:
            plan_text = parsed.get("plan")
            if isinstance(plan_text, str):
                normalized_plan = plan_text
            else:
                normalized_plan = json.dumps(plan_text if plan_text is not None else parsed, ensure_ascii=False, indent=2)

            suggested_sources = cls._normalize_sources(parsed.get("suggested_sources"))
            return {
                "plan": normalized_plan,
                "suggested_sources": suggested_sources,
            }

        return {
            "plan": raw_plan.strip(),
            "suggested_sources": [],
        }

    @classmethod
    def _infer_sources_from_plan_text(cls, plan_text: str) -> list[str]:
        inferred: list[str] = []
        for alias, canonical in _SOURCE_ALIASES.items():
            if alias in plan_text.lower() and canonical not in inferred:
                inferred.append(canonical)
        return inferred

    async def generate_collection_plan(self, pir: str, modifications: str | None = None) -> str:
        """Generate plan and always return canonical JSON for frontend/backend consumers."""
        async with self.mcp_client.connect():
            system_prompt = await self.mcp_client.get_prompt(
                "collection_plan",
                {
                    "pir": pir,
                    "modifications": modifications or "",
                },
            )
            agent = GeminiAgent(self.mcp_client)
            ai_output = await agent.run(
                system_prompt=system_prompt,
                task="Generate a collection plan and suggest relevant sources for the given PIRs.",
            )

        payload = self._coerce_plan_payload(ai_output)

        # If AI missed suggested sources, infer from plan text and default to local KB.
        if not payload["suggested_sources"]:
            payload["suggested_sources"] = self._infer_sources_from_plan_text(payload["plan"]) or [_DEFAULT_SOURCE]

        return json.dumps(payload, ensure_ascii=False)

    async def suggest_sources(self, plan_json: str) -> list[str]:
        """Parse suggested sources from plan output without throwing on malformed JSON."""
        try:
            payload = self._coerce_plan_payload(plan_json)
            sources = payload.get("suggested_sources", [])

            if not sources:
                sources = self._infer_sources_from_plan_text(payload.get("plan", ""))

            if not sources:
                return [_DEFAULT_SOURCE]

            return sources
        except Exception:
            logger.exception("[CollectionService] Failed to parse suggested sources. Falling back to default source.")
            return [_DEFAULT_SOURCE]

    async def collect(
        self,
        selected_sources: list[str],
        pir: str,
        plan: str,
        language: str = "en",
        feedback: str | None = None,
        session_id: str | None = None,
        timeframe: str = "",
        existing_raw_data: str | None = None,
        perspectives: list[str] | None = None,
    ) -> str:
        """Collect raw data only — no summarization.

        existing_raw_data: data already gathered in previous attempts (passed for context).
        """
        payload = self._coerce_plan_payload(plan)
        plan_text = payload.get("plan", plan)

        async with self.mcp_client.connect():
            collect_prompt = await self.mcp_client.get_prompt(
                "collection_collect",
                {
                    "pir": pir,
                    "selected_sources": json.dumps(selected_sources),
                    "plan": plan_text,
                    "session_id": session_id or "",
                    "since_date": timeframe,
                    "existing_data": existing_raw_data or "",
                    "perspectives": json.dumps(perspectives or []),
                },
            )
            agent = GeminiAgent(self.mcp_client)
            task = "Collect raw intelligence data from the approved sources based on the PIRs."
            if feedback:
                task += f" REVIEWER FEEDBACK FROM PREVIOUS ATTEMPT: {feedback}"
            raw_data = await agent.run(
                system_prompt=collect_prompt,
                task=task,
            )

        return raw_data

    async def modify_summary(self, collected_data: str, modifications: str) -> str:
        async with self.mcp_client.connect():
            system_prompt = await self.mcp_client.get_prompt(
                "collection_modify",
                {
                    "collected_data": collected_data,
                    "modifications": modifications,
                },
            )
            agent = GeminiAgent(self.mcp_client)
            ai_output = await agent.run(
                system_prompt=system_prompt,
                task="Apply the requested modifications to the existing intelligence summary.",
            )
        return ai_output
