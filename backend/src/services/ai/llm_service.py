"""LLMService direct Gemini API calls for the Direction phase.

This service is used by DialogueService and ReviewService for all
Direction phase AI generation. No MCP is involved.

Collection and Processing phases use GeminiAgent instead, which
communicates with the MCP server via the MCP protocol.
"""

import json
import logging
import os
import re

from google import genai

logger = logging.getLogger("app")


def _repair_json(text: str) -> str:
    """Apply a sequence of increasingly aggressive repairs to LLM generated JSON.

    Repair 1: Replace typographic quotes with ASCII equivalents.
    Repair 2: Remove backslashes before characters that are not valid JSON escape targets.
    Repair 3: Strip trailing commas before ] or }.
    Repair 4: Escape unescaped inner quotes inside string values.
    """
    # Repair 1
    text = (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )

    # Repair 2
    text = re.sub(r"\\([^\"\\\/bfnrtu])", r"\1", text)

    # Repair 3
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Repair 4
    result: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != '"':
            result.append(ch)
            i += 1
            continue

        # Opening quote of a string  copy it and scan the contents.
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


class LLMService:
    """Direct Gemini API wrapper for backend AI calls.

    Used in the direction phase to call Gemini directly. This is used when MCP is not needed.

    """

    def __init__(self, model: str = "gemini-2.5-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def generate_text(self, prompt: str) -> str:
        """Send a prompt to Gemini and return the raw text response.

        Args:
            prompt: The prompt string to send to the model.

        Returns:
            The model's text response.

        Raises:
            ValueError: If the model returns an empty response.
        """
        logger.debug(f"[LLMService] Calling {self.model} (text)")
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        if not response.text:
            raise ValueError(f"[LLMService] {self.model} returned empty response")
        return response.text

    async def generate_json(self, prompt: str) -> dict:
        """Send a prompt to Gemini and return the JSON response.

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

        # First parse failed. Attempt to repair and try again
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
        """Strip markdown code fences and trailing content from a response string."""
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
