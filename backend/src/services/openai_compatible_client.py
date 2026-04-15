"""Small async client for OpenAI-compatible chat-completions APIs."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.services.llm_config import LLMConfig, get_llm_config

logger = logging.getLogger("app")


class OpenAICompatibleClient:
    """Minimal wrapper around `/chat/completions`.

    The app only needs plain generation and tool-calling responses, so using
    httpx directly keeps the provider swap local and avoids pulling in a second
    SDK.
    """

    def __init__(self, config: LLMConfig | None = None, model: str | None = None):
        self.config = config or get_llm_config(model=model)
        self.base_url = self.config.base_url.rstrip("/")
        self.model = self.config.model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        url = f"{self.base_url}/chat/completions"
        logger.debug("[OpenAICompatibleClient] POST %s model=%s", url, self.model)

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            try:
                response = await self._post_chat(client, url, headers, body)
            except httpx.HTTPStatusError as exc:
                if not tools or not self._is_tool_support_error(exc.response):
                    raise

                logger.warning(
                    "[OpenAICompatibleClient] Provider rejected tool-calling metadata; "
                    "retrying without native tools. To enable MCP tool-calling with "
                    "vLLM, start it with --enable-auto-tool-choice and the matching "
                    "--tool-call-parser for the model."
                )
                fallback_body = dict(body)
                fallback_body.pop("tools", None)
                fallback_body.pop("tool_choice", None)
                response = await self._post_chat(client, url, headers, fallback_body)
            payload = response.json()

        choices = payload.get("choices") or []
        if not choices:
            raise ValueError(f"Model {self.model} returned no choices")
        return choices[0].get("message") or {}

    async def generate_text(self, prompt: str) -> str:
        message = await self.chat([{"role": "user", "content": prompt}])
        text = message.get("content")
        if not text:
            raise ValueError(f"Model {self.model} returned empty response")
        return str(text)

    async def _post_chat(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> httpx.Response:
        response = await client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            logger.error(
                "[OpenAICompatibleClient] HTTP %s: %s",
                response.status_code,
                response.text[:500],
            )
        response.raise_for_status()
        return response

    @staticmethod
    def _is_tool_support_error(response: httpx.Response) -> bool:
        if response.status_code not in {400, 422}:
            return False
        text = response.text.lower()
        return any(
            phrase in text
            for phrase in (
                "tool choice requires",
                "enable-auto-tool-choice",
                "tool-call-parser",
                "tools is not supported",
                "tool_calls is not supported",
                "does not support tools",
            )
        )
