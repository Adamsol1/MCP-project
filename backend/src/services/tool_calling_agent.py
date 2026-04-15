"""OpenAI-compatible tool-calling agent for MCP-backed phases."""

from __future__ import annotations

import html
import json
import logging
import re
from typing import Any

import httpx

from src.services.openai_compatible_client import OpenAICompatibleClient

logger = logging.getLogger("app")


def _json_schema_for_openai(schema: dict[str, Any]) -> dict[str, Any]:
    if not schema:
        return {"type": "object", "properties": {}}
    if schema.get("type") != "object":
        return {"type": "object", "properties": {}}
    return schema


def _strip_json_fence(text: str) -> str:
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    return fence.group(1).strip() if fence else text.strip()


def _parse_tool_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "[ToolCallingAgent] Could not parse tool arguments: %s", raw[:200]
            )
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _extract_html_text(raw_html: str) -> tuple[str | None, str]:
    title_match = re.search(
        r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL
    )
    title = (
        html.unescape(re.sub(r"\s+", " ", title_match.group(1)).strip())
        if title_match
        else None
    )

    text = re.sub(
        r"<(script|style|noscript)[^>]*>[\s\S]*?</\1>",
        " ",
        raw_html,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return title, text


class ToolCallingAgent:
    """Run an MCP tool loop using an OpenAI-compatible local model."""

    def __init__(
        self,
        mcp_client,
        model: str | None = None,
        max_tool_rounds: int = 50,
    ):
        self.client = OpenAICompatibleClient(model=model)
        self.model = self.client.model
        self.mcp_client = mcp_client
        self.max_tool_rounds = max_tool_rounds

    async def run(
        self,
        system_prompt: str,
        task: str,
        allowed_tool_names: set[str] | None = None,
        status_tracker=None,
    ) -> str:
        available_tools = await self._get_tool_declarations(allowed_tool_names)
        logger.info(
            "[ToolCallingAgent] Starting run with %s tools available",
            len(available_tools),
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ]
        last_text = ""

        for round_num in range(self.max_tool_rounds):
            message = await self.client.chat(messages, tools=available_tools)
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                text = str(message.get("content") or "")
                logger.info(
                    "[ToolCallingAgent] Completed in %s round(s)", round_num + 1
                )
                return text

            logger.info(
                "[ToolCallingAgent] Round %s: %s tool call(s)",
                round_num + 1,
                len(tool_calls),
            )
            last_text = str(message.get("content") or "")

            assistant_tool_calls: list[dict[str, Any]] = []
            tool_result_messages: list[dict[str, Any]] = []
            for index, tool_call in enumerate(tool_calls):
                call_id = tool_call.get("id") or f"call_{round_num}_{index}"
                function = tool_call.get("function") or {}
                name = function.get("name")
                args = _parse_tool_arguments(function.get("arguments"))
                if not name:
                    continue

                assistant_tool_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(args),
                        },
                    }
                )

                _args_safe = (
                    repr(args)
                    .encode("ascii", errors="backslashreplace")
                    .decode("ascii")
                )
                logger.info("[ToolCallingAgent] Calling tool: %s(%s)", name, _args_safe)
                if status_tracker is not None:
                    status_tracker.record_tool_call(name, args)

                try:
                    result = await self.mcp_client.call_tool(name, args)
                    result_text = (
                        result if isinstance(result, str) else json.dumps(result)
                    )
                except Exception as exc:
                    result_text = f"Tool error: {type(exc).__name__}: {exc}"
                    logger.error("[ToolCallingAgent] Tool %s failed: %s", name, exc)

                tool_result_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": result_text,
                    }
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": last_text,
                    "tool_calls": assistant_tool_calls,
                }
            )
            messages.extend(tool_result_messages)

        logger.warning(
            "[ToolCallingAgent] Max tool rounds (%s) reached",
            self.max_tool_rounds,
        )
        return last_text or "Agent reached maximum tool iterations without completing."

    _INACCESSIBLE_PHRASES: tuple[str, ...] = (
        "not accessible",
        "unable to access",
        "cannot access",
        "could not access",
        "access denied",
        "access is denied",
        "403",
        "404 not found",
        "page not found",
        "could not fetch",
        "failed to fetch",
        "error fetching",
        "blocked",
        "paywall",
        "subscription required",
        "behind a paywall",
        "login required",
        "sign in required",
        "no content available",
    )

    async def fetch_url_summaries(
        self,
        urls: list[str],
        pir: str,
        perspectives: list[str],
        batch_size: int = 15,
    ) -> list[dict[str, Any]]:
        """Fetch web pages locally and summarize them with the configured model."""
        if not urls:
            return []

        del batch_size  # Kept for call-site compatibility.
        results: list[dict[str, Any]] = []
        for url in urls:
            page = await self._fetch_page_text(url)
            if page is None:
                continue

            title, page_text = page
            prompt = self._build_page_summary_prompt(
                url=url,
                title=title,
                page_text=page_text[:12000],
                pir=pir,
                perspectives=perspectives,
            )

            try:
                text = await self.client.generate_text(prompt)
                parsed = json.loads(_strip_json_fence(text))
            except Exception as exc:
                logger.error(
                    "[ToolCallingAgent] URL summary failed for %s: %s", url, exc
                )
                parsed = {
                    "url": url,
                    "title": title or url,
                    "author": None,
                    "date": None,
                    "publisher": None,
                    "apa_citation": url,
                    "summary": page_text[:1000],
                }

            summary = str(parsed.get("summary") or "")
            if not summary or any(
                phrase in summary.lower() for phrase in self._INACCESSIBLE_PHRASES
            ):
                continue

            citation = str(parsed.get("apa_citation") or url)
            content = f"[{parsed.get('title') or title or 'Article'}]\n{summary}"
            if citation:
                content += f"\n\nCitation: {citation}"
            results.append(
                {
                    "source": "fetch_page",
                    "resource_id": parsed.get("url") or url,
                    "content": content,
                    "apa_citation": citation,
                    "author": parsed.get("author"),
                    "date": parsed.get("date"),
                    "publisher": parsed.get("publisher"),
                    "title": parsed.get("title") or title,
                }
            )

        return results

    async def _fetch_page_text(self, url: str) -> tuple[str | None, str] | None:
        headers = {
            "User-Agent": "MCP-project/1.0 (+local analysis workflow)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
        }
        try:
            async with httpx.AsyncClient(
                timeout=20,
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = await client.get(url)
            if response.status_code >= 400:
                logger.info(
                    "[ToolCallingAgent] Skipping %s: HTTP %s", url, response.status_code
                )
                return None
            content_type = response.headers.get("content-type", "").lower()
            if content_type and not any(
                kind in content_type for kind in ("html", "text", "xml")
            ):
                logger.info(
                    "[ToolCallingAgent] Skipping %s: content-type %s", url, content_type
                )
                return None
            title, text = _extract_html_text(response.text)
            if len(text) < 200:
                return None
            return title, text
        except Exception as exc:
            logger.info("[ToolCallingAgent] Could not fetch %s: %s", url, exc)
            return None

    def _build_page_summary_prompt(
        self,
        *,
        url: str,
        title: str | None,
        page_text: str,
        pir: str,
        perspectives: list[str],
    ) -> str:
        perspectives_str = ", ".join(perspectives) if perspectives else "neutral"
        return f"""
PIR (Priority Intelligence Requirement): {pir}
Analysis perspectives: {perspectives_str}

Read the fetched page text below and extract intelligence-relevant information.
Return ONLY valid JSON with this exact shape:
{{
  "url": "{url}",
  "title": "string",
  "author": "string or null",
  "date": "YYYY-MM-DD or null",
  "publisher": "string or null",
  "apa_citation": "string",
  "summary": "3-5 sentences focused on facts and analysis directly relevant to the PIR"
}}

If metadata is unavailable, use null. Do not invent facts.

URL: {url}
Detected title: {title or ""}

Fetched page text:
{page_text}
""".strip()

    async def _get_tool_declarations(
        self,
        allowed_tool_names: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        raw_tools = await self.mcp_client.list_tools()
        declarations: list[dict[str, Any]] = []
        for tool in raw_tools:
            if (
                allowed_tool_names is not None
                and tool["name"] not in allowed_tool_names
            ):
                continue
            declarations.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": _json_schema_for_openai(
                            tool.get("inputSchema", {})
                        ),
                    },
                }
            )
        return declarations
