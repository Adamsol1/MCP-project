"""LLMService — direct Gemini API calls for the Direction phase.

This service is used by DialogueService and ReviewService for all
Direction phase AI generation. No MCP is involved.

Collection and Processing phases use GeminiAgent instead, which
communicates with the MCP server via the MCP protocol.
"""

import json
import logging
import os

from google import genai

logger = logging.getLogger("app")


class LLMService:
    """Direct Gemini API wrapper for backend AI calls.

    Used exclusively in the Direction phase where no external tool
    integration is needed. Wraps google-genai with async support
    and JSON parsing convenience.
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
        """Send a prompt to Gemini and return the parsed JSON response.

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
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"[LLMService] Model did not return valid JSON: {e}\nResponse: {text[:200]}")
            raise

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Strip markdown code fences from a response string."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1])
        return text
