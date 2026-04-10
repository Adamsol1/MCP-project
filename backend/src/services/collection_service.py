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
from pathlib import Path
from typing import Any

from src.mcp_client.client import MCPClient
from src.services.collection_status import CollectionStatusTracker
from src.services.gemini_agent import GeminiAgent

logger = logging.getLogger("app")

_DEFAULT_SOURCE = "Internal Knowledge Bank"
_SESSIONS_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "sessions"

# Maps UI source names to the MCP tool names they are allowed to call.
# Must stay in sync with SOURCE_TOOL_MAP in mcp_server/src/prompts/__init__.py.
_SOURCE_TO_TOOLS: dict[str, list[str]] = {
    "Internal Knowledge Bank": ["list_knowledge_base", "read_knowledge_base"],
    "AlienVault OTX": ["query_otx"],
    "Uploaded Documents": ["list_uploads", "search_local_data", "read_upload"],
    "Web Search": ["google_search"],
}


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
    (("google", "search"),   "Web Search"),
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
    "google search": "Web Search",
}

TOOL_TO_DISPLAY_NAME: dict[str, str] = {
    "list_knowledge_base": "Internal Knowledge Bank",
    "read_knowledge_base": "Internal Knowledge Bank",
    "query_otx": "AlienVault OTX",
    "search_local_data": "Uploaded Documents",
    "list_uploads": "Uploaded Documents",
    "read_upload": "Uploaded Documents",
    "google_search": "Web Search",
    "google_news_search": "Web News",
    "fetch_page": "Web Fetch",
}


def _extract_search_urls(raw_data: str) -> list[str]:
    """Extract unique URLs from google_search and google_news_search tool results.

    Handles two output formats:
    - Legacy / partial copy: tool text includes "URL: https://..." lines
    - Current format: model puts URL in "resource_id" JSON field
    Both are searched so the second-pass fetch runs regardless of which format
    the model used.
    """
    # Format 1 — legacy text: "URL: https://..."
    text_urls = re.findall(r"URL:\s*(https?://\S+)", raw_data)
    # Format 2 — JSON resource_id field containing an HTTP URL
    resource_ids = re.findall(r'"resource_id"\s*:\s*"(https?://[^"]+)"', raw_data)

    seen: set[str] = set()
    unique: list[str] = []
    for url in text_urls + resource_ids:
        url = url.rstrip(".,)")
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _try_parse_json_lenient(s: str) -> dict | None:
    """Try json.loads; on failure apply common LLM-output repairs and retry."""
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Remove invalid JSON escape sequences (e.g. \' produced by some LLMs —
    # only \", \\, \/, \b, \f, \n, \r, \t, \uXXXX are valid in JSON).
    repaired = re.sub(r"\\([^\"\\\/bfnrtu])", r"\1", s)
    # Strip trailing commas before ] or }
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


_SEARCH_SNIPPET_SOURCES = {"google_search", "google_news_search"}


def _strip_search_snippet_items(raw_data: str) -> str:
    """Remove google_search snippet items from collected_data.

    After the url_context fetch pass, the Serper snippets are no longer needed —
    only the fetch_page summaries carry real intelligence value.
    Returns the modified JSON string, or the original if parsing fails.
    """
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_data, re.IGNORECASE)
    json_str = fence.group(1).strip() if fence else raw_data.strip()

    parsed = _try_parse_json_lenient(json_str)
    if parsed is None:
        return raw_data

    original_count = len(parsed.get("collected_data", []))
    parsed["collected_data"] = [
        item for item in parsed.get("collected_data", [])
        if item.get("source") not in _SEARCH_SNIPPET_SOURCES
    ]
    stripped_count = original_count - len(parsed["collected_data"])
    if stripped_count:
        logger.info(f"[CollectionService] Stripped {stripped_count} Serper snippet items from collected_data")
    return json.dumps(parsed, ensure_ascii=False)


def _append_to_collected_data(raw_data: str, extra_items: list[dict]) -> str:
    """Insert additional items into the collected_data list in raw_data JSON."""
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_data, re.IGNORECASE)
    json_str = fence.group(1).strip() if fence else raw_data.strip()

    parsed = _try_parse_json_lenient(json_str)
    if parsed is not None:
        parsed["collected_data"] = parsed.get("collected_data", []) + extra_items
        return json.dumps(parsed, ensure_ascii=False)

    logger.warning("[CollectionService] _append_to_collected_data: could not parse base JSON, appending separately")
    return raw_data + "\n" + json.dumps({"collected_data": extra_items}, ensure_ascii=False)


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

            # Multi-attempt accumulation: orchestrator joins attempts with this separator.
            # Split, parse each segment independently, then merge all collected_data lists.
            _SEPARATOR = "--- NEW COLLECTION ATTEMPT ---"
            if _SEPARATOR in stripped:
                segments = [s.strip() for s in stripped.split(_SEPARATOR) if s.strip()]
                items = []
                for seg in segments:
                    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", seg, re.IGNORECASE)
                    seg_text = fence.group(1).strip() if fence else seg
                    seg_parsed = _try_parse_json_lenient(seg_text) if seg_text else None
                    # If fence regex failed (e.g. closing ``` split away), extract by braces
                    if seg_parsed is None:
                        start, end = seg.find("{"), seg.rfind("}")
                        if 0 <= start < end:
                            seg_parsed = _try_parse_json_lenient(seg[start : end + 1])
                    if seg_parsed and isinstance(seg_parsed.get("collected_data"), list):
                        items.extend(seg_parsed["collected_data"])
            else:
                fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, re.IGNORECASE)
                if fence_match:
                    stripped = fence_match.group(1).strip()
                parsed = _try_parse_json_lenient(stripped) if stripped else {}
                if parsed is None:
                    # Last resort: extract largest {...} block
                    start, end = stripped.find("{"), stripped.rfind("}")
                    if 0 <= start < end:
                        parsed = _try_parse_json_lenient(stripped[start:end + 1])
                if not parsed:
                    raise json.JSONDecodeError("Could not repair JSON", stripped, 0)
                items = parsed.get("collected_data", [])

            if not isinstance(items, list):
                raise ValueError("collected_data is not a list")

            # Unwrap MCP response wrappers the model occasionally embeds in content.
            # Pattern: {"result": "text"} or {"tool_response": {"result": "text"}}
            for item in items:
                raw_content = item.get("content", "")
                if isinstance(raw_content, str) and raw_content.startswith("{"):
                    try:
                        inner = json.loads(raw_content)
                        if isinstance(inner, dict):
                            if "result" in inner and isinstance(inner["result"], str):
                                item["content"] = inner["result"]
                            elif len(inner) == 1:
                                val = next(iter(inner.values()))
                                if isinstance(val, dict) and isinstance(val.get("result"), str):
                                    item["content"] = val["result"]
                                elif isinstance(val, str):
                                    item["content"] = val
                    except Exception:
                        pass

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
            result: dict[str, Any] = {
                "plan": normalized_plan,
                "suggested_sources": suggested_sources,
            }
            if isinstance(parsed.get("steps"), list):
                result["steps"] = parsed["steps"]
            return result

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
        tracker = None

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
            allowed_tool_names = {
                tool
                for source in selected_sources
                for tool in _SOURCE_TO_TOOLS.get(source, [])
            }

            if session_id:
                tracker = CollectionStatusTracker(session_id, selected_sources)

            agent = GeminiAgent(self.mcp_client)
            task = "Collect raw intelligence data from the approved sources based on the PIRs."
            if feedback:
                task += f" REVIEWER FEEDBACK FROM PREVIOUS ATTEMPT: {feedback}"

            raw_data = await agent.run(
                system_prompt=collect_prompt,
                task=task,
                allowed_tool_names=allowed_tool_names,
                status_tracker=tracker,
            )

        if tracker:
            tracker.mark_complete()

        # Second pass: summarize full page content via Gemini url_context (no scraping).
        # Runs outside the MCP context — url_context is a Gemini built-in, not an MCP tool.
        # We pass up to 25 URLs (buffer) because some pages will be inaccessible and get
        # filtered out inside fetch_url_summaries, so we need extras to hit the ~15 target.
        if "Web Search" in selected_sources:
            urls = _extract_search_urls(raw_data)
            if urls:
                url_agent = GeminiAgent(self.mcp_client)
                _url_buffer = min(len(urls), 25)
                logger.info(
                    f"[CollectionService] url_context: fetching {_url_buffer} of {len(urls)} URLs (buffer for inaccessible pages)"
                )
                summaries = await url_agent.fetch_url_summaries(
                    urls=urls[:_url_buffer],
                    pir=pir,
                    perspectives=perspectives or [],
                )
                if summaries:
                    raw_data = _append_to_collected_data(raw_data, summaries)
                    logger.info(
                        f"[CollectionService] url_context: added {len(summaries)} page summaries"
                    )

            raw_data = _strip_search_snippet_items(raw_data)

        return raw_data

    @staticmethod
    def delete_web_results(session_id: str) -> None:
        """Remove the collected data file for a session."""
        doc_path = _SESSIONS_DATA_DIR / session_id / "collected.json"
        if doc_path.exists():
            doc_path.unlink()

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
