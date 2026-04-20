"""LLMService - direct OpenAI-compatible LLM calls.

This service is used by DialogueService and ReviewService for plain text/JSON
generation. No MCP is involved.

Collection and Processing phases use ToolCallingAgent instead, which
communicates with the MCP server via the MCP protocol.
"""

import json
import logging
import os
import re

from src.services.llm_config import (
    get_default_gemini_model,
    get_llm_config,
    get_llm_provider,
)
from src.services.openai_compatible_client import OpenAICompatibleClient

logger = logging.getLogger("app")


def _repair_json(text: str) -> str:
    """Apply a sequence of increasingly aggressive repairs to LLM-generated JSON.

    Repair 1 — Python literals: local models often emit Python-style None, True,
               False instead of JSON null, true, false.
    Repair 2 — smart/curly quotes: replace typographic " " ' ' with ASCII equivalents.
    Repair 3 — bad escape sequences: remove backslashes before characters that are not
               valid JSON escape targets (e.g. \' produced by some models).
    Repair 4 — trailing commas: strip commas immediately before ] or }.
    Repair 5 — unescaped inner quotes: scan character-by-character; when inside a JSON
               string, any " not immediately followed by a JSON structural character
               (, } ] : or end-of-input) is treated as an unescaped quote and gets
               escaped to \".
    """
    # Repair 1: Python literals → JSON equivalents
    # Only replace when NOT inside a quoted string (word-boundary match).
    text = re.sub(r'\bNone\b', 'null', text)
    text = re.sub(r'\bTrue\b', 'true', text)
    text = re.sub(r'\bFalse\b', 'false', text)

    # Repair 2: typographic quotes → ASCII
    text = (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )

    # Repair 3: invalid escape sequences (e.g. \' → ')
    text = re.sub(r"\\([^\"\\\/bfnrtu])", r"\1", text)

    # Repair 4: trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Repair 5: unescaped double quotes inside string values.
    # Heuristic: when inside a string, a " is the closing quote only when
    # the next non-whitespace char is a JSON structural character (, } ] :)
    # or the text ends.  Otherwise it is escaped.
    result: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != '"':
            result.append(ch)
            i += 1
            continue

        # Opening quote of a string — copy it and scan the contents.
        result.append('"')
        i += 1
        while i < n:
            ch = text[i]
            if ch == "\\":
                # Valid escape: copy both chars verbatim.
                result.append(ch)
                i += 1
                if i < n:
                    result.append(text[i])
                    i += 1
            elif ch == '"':
                # Look ahead past whitespace to decide if this closes the string.
                j = i + 1
                while j < n and text[j] in " \t\r\n":
                    j += 1
                if j >= n or text[j] in ",}]:":
                    result.append('"')
                    i += 1
                    break  # end of string
                else:
                    # Unescaped inner quote — escape it.
                    result.append('\\"')
                    i += 1
            else:
                result.append(ch)
                i += 1

    return "".join(result)


class GeminiTextClient:
    """Minimal async Gemini text client used for non-tool LLM calls."""

    def __init__(self, model: str | None = None):
        from google import genai

        self.model = model or get_default_gemini_model()
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    async def generate_text(self, prompt: str) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        text = getattr(response, "text", None)
        if text:
            return str(text)

        candidates = getattr(response, "candidates", None) or []
        if candidates and getattr(candidates[0], "content", None):
            parts = getattr(candidates[0].content, "parts", []) or []
            text = "".join(str(part.text) for part in parts if getattr(part, "text", None))
            if text:
                return text
        raise ValueError(f"Model {self.model} returned empty response")


class LLMService:
    """Direct OpenAI-compatible API wrapper for backend AI calls.

    Used where no external tool integration is needed. Provides async text
    generation and JSON parsing convenience.
    """

    def __init__(self, model: str | None = None):
        provider = get_llm_provider()
        if provider == "gemini":
            self.client = GeminiTextClient(model=model)
        else:
            self.client = OpenAICompatibleClient(config=get_llm_config(model=model))
        self.provider = provider
        self.model = self.client.model

    async def generate_text(self, prompt: str) -> str:
        """Send a prompt to the configured model and return the raw text response.

        Args:
            prompt: The prompt string to send to the model.

        Returns:
            The model's text response.

        Raises:
            ValueError: If the model returns an empty response.
        """
        logger.debug(f"[LLMService] Calling {self.model} (text)")
        return await self.client.generate_text(prompt)

    async def generate_json(self, prompt: str) -> dict:
        """Send a prompt to the configured model and return the parsed JSON response.

        Args:
            prompt: The prompt string to send to the model.

        Returns:
            Parsed JSON as a dict.

        Raises:
            ValueError: If the model returns an empty response.
            json.JSONDecodeError: If the response is not valid JSON.
        """
        text = await self.generate_text(prompt)
        text = self._strip_fences(text)
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # First parse failed — apply repairs and retry.
        repaired = _repair_json(text)
        try:
            result = json.loads(repaired)
            logger.debug("[LLMService] JSON parsed after repair pass")
            if isinstance(result, dict):
                return result
            raise json.JSONDecodeError("Expected a JSON object", repaired, 0)
        except json.JSONDecodeError as e:
            logger.error(
                f"[LLMService] Model did not return valid JSON: {e}\nResponse: {text[:200]}"
            )
            raise

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Strip markdown code fences and trailing non-JSON content from a response string."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        # Extract the outermost JSON object or array, discarding any trailing text.
        for start_char, end_char in (("{", "}"), ("[", "]")):
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                return text[start : end + 1]
        return text
