"""GeminiProvider — wraps the Google Gemini SDK behind the LLMProvider interface."""

from __future__ import annotations

from typing import Any

from google.genai import types

from src.services.ai.gemini_agent import GeminiAgent
from src.services.ai.gemini_client import create_gemini_client
from src.services.ai.llm_config import get_default_gemini_model


class GeminiProvider:
    name = "gemini"

    def __init__(self, model: str | None = None):
        self.model = model or get_default_gemini_model()
        self._client = create_gemini_client()

    async def generate_text(self, prompt: str) -> str:
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return self._extract_text(response, allow_empty=False)

    async def generate_json_text(self, prompt: str) -> str:
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return self._extract_text(response, allow_empty=False)

    async def chat(self, messages: list[dict[str, Any]]) -> str:
        system_instruction = "\n\n".join(
            str(m.get("content", ""))
            for m in messages
            if m.get("role") == "system"
        )
        contents = [
            types.Content(
                role="model" if m.get("role") == "assistant" else "user",
                parts=[types.Part(text=str(m.get("content", "")))],
            )
            for m in messages
            if m.get("role") != "system"
        ]
        if not contents:
            raise ValueError("At least one user or assistant message is required")

        kwargs: dict[str, Any] = {"model": self.model, "contents": contents}
        if system_instruction:
            kwargs["config"] = types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        response = await self._client.aio.models.generate_content(**kwargs)
        return self._extract_text(response, allow_empty=False)

    def tool_agent(self, mcp_client: Any, max_tool_rounds: int = 50) -> GeminiAgent:
        return GeminiAgent(
            mcp_client,
            model=self.model,
            max_tool_rounds=max_tool_rounds,
        )

    def _extract_text(self, response: Any, *, allow_empty: bool) -> str:
        text = getattr(response, "text", None)
        if text:
            return str(text)
        candidates = getattr(response, "candidates", None) or []
        if candidates and getattr(candidates[0], "content", None):
            parts = getattr(candidates[0].content, "parts", []) or []
            joined = "".join(
                str(part.text) for part in parts if getattr(part, "text", None)
            )
            if joined:
                return joined
        if allow_empty:
            return ""
        raise ValueError(f"Model {self.model} returned empty response")
