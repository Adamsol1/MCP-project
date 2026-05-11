"""LLMService - direct LLM calls (text + JSON) via the active provider.

Used by DialogueService and ReviewService for plain text/JSON generation.
No MCP is involved here; the actual provider (Gemini, OpenAI-compatible, …)
is selected by `providers.get_provider()`.

Collection and Processing phases use the provider's `tool_agent()` instead,
which communicates with the MCP server via the MCP protocol.
"""

import json
import logging
import re

from src.services.ai.providers import LLMProvider, get_provider

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
    text = re.sub(r'\bNone\b', 'null', text)
    text = re.sub(r'\bTrue\b', 'true', text)
    text = re.sub(r'\bFalse\b', 'false', text)

    # Repair 2: typographic quotes → ASCII
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )

    # Repair 3: invalid escape sequences (e.g. \' → ')
    text = re.sub(r"\\([^\"\\\/bfnrtu])", r"\1", text)

    # Repair 4: trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Repair 5: unescaped double quotes inside string values.
    result: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != '"':
            result.append(ch)
            i += 1
            continue

        result.append('"')
        i += 1
        while i < n:
            ch = text[i]
            if ch == "\\":
                result.append(ch)
                i += 1
                if i < n:
                    result.append(text[i])
                    i += 1
            elif ch == '"':
                j = i + 1
                while j < n and text[j] in " \t\r\n":
                    j += 1
                if j >= n or text[j] in ",}]:":
                    result.append('"')
                    i += 1
                    break
                else:
                    result.append('\\"')
                    i += 1
            else:
                result.append(ch)
                i += 1

    return "".join(result)


class LLMService:
    """Provider-agnostic wrapper for backend AI calls without MCP tools.

    The concrete backend (Gemini, OpenAI-compatible, …) is resolved through
    `providers.get_provider()`, so a per-request `ai_provider` override applied
    via `request_llm_provider(...)` is honored automatically.
    """

    def __init__(
        self,
        model: str | None = None,
        provider: LLMProvider | None = None,
    ):
        self.provider = provider or get_provider(model=model)
        self.model = self.provider.model

    async def generate_text(self, prompt: str) -> str:
        """Send a prompt to the active model and return the raw text response."""
        logger.debug(f"[LLMService] Calling {self.model} (text)")
        return await self.provider.generate_text(prompt)

    async def generate_json(self, prompt: str) -> dict:
        """Send a prompt and return a parsed JSON object."""
        text = await self.provider.generate_json_text(prompt)
        text = self._strip_fences(text)
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

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
        """Strip markdown fences and extract the first JSON object from a response."""
        text = text.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
        if fence:
            text = fence.group(1).strip()

        json_object = LLMService._extract_first_json_object(text)
        return json_object or text

    @staticmethod
    def _extract_first_json_object(text: str) -> str | None:
        """Return the first balanced JSON object substring, if one exists."""
        for start, ch in enumerate(text):
            if ch != "{":
                continue

            depth = 0
            in_string = False
            escaped = False
            for index in range(start, len(text)):
                ch = text[index]
                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        in_string = False
                    continue

                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start : index + 1]

        return None
