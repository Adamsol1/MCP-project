"""Small async client for OpenAI-compatible chat-completions APIs."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from src.services.ai.llm_config import LLMConfig, get_llm_config

logger = logging.getLogger("app")


class OpenAICompatibleClient:
    """Minimal wrapper around `/chat/completions`.

    The app only needs plain generation and tool-calling responses, so using
    httpx directly keeps the provider swap local and avoids pulling in a second
    SDK.
    """

    # Class-level flag: once we learn that the provider does not support tool
    # calling, skip sending tools on all subsequent requests to avoid a
    # wasted 400 round-trip on every single call.
    _tools_supported: bool = True
    _json_response_format_supported: bool = True

    def __init__(self, config: LLMConfig | None = None, model: str | None = None):
        self.config = config or get_llm_config(model=model)
        self.base_url = self.config.base_url.rstrip("/")
        self.model = self.config.model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Strip tools if the provider already told us it doesn't support them.
        if not OpenAICompatibleClient._tools_supported:
            tools = None
        if not OpenAICompatibleClient._json_response_format_supported:
            response_format = None

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        if self.config.max_completion_tokens is not None:
            body["max_completion_tokens"] = self.config.max_completion_tokens
        if self.config.enable_thinking is not None:
            body["chat_template_kwargs"] = {
                "enable_thinking": self.config.enable_thinking
            }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if response_format:
            body["response_format"] = response_format

        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        url = f"{self.base_url}/chat/completions"
        logger.debug("[OpenAICompatibleClient] POST %s model=%s", url, self.model)

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            while True:
                try:
                    response = await self._post_chat(client, url, headers, body)
                    break
                except httpx.RemoteProtocolError:
                    if "tools" in body:
                        OpenAICompatibleClient._tools_supported = False
                        logger.info(
                            "[OpenAICompatibleClient] Provider disconnected when "
                            "tool-calling metadata was sent; disabling tools for "
                            "subsequent requests."
                        )
                        body.pop("tools", None)
                        body.pop("tool_choice", None)
                        continue
                    raise RuntimeError(
                        "The configured local LLM endpoint disconnected without "
                        f"sending a response: {url}."
                    ) from None
                except httpx.HTTPStatusError as exc:
                    if "tools" in body and self._is_tool_support_error(exc.response):
                        OpenAICompatibleClient._tools_supported = False
                        logger.info(
                            "[OpenAICompatibleClient] Provider rejected tool-calling "
                            "metadata; disabling tools for subsequent requests. To "
                            "enable MCP tool-calling with vLLM, start it with "
                            "--enable-auto-tool-choice and the matching "
                            "--tool-call-parser for the model."
                        )
                        body.pop("tools", None)
                        body.pop("tool_choice", None)
                        continue
                    if "response_format" in body and self._is_json_mode_error(
                        exc.response
                    ):
                        OpenAICompatibleClient._json_response_format_supported = False
                        logger.warning(
                            "[OpenAICompatibleClient] Provider rejected JSON response "
                            "format metadata; retrying without response_format."
                        )
                        body.pop("response_format", None)
                        continue
                    logger.error(
                        "[OpenAICompatibleClient] HTTP %s: %s",
                        exc.response.status_code,
                        exc.response.text[:500],
                    )
                    if exc.response.status_code == 502:
                        raise RuntimeError(
                            "The configured local LLM endpoint returned 502 Bad "
                            "Gateway. The Vast/vLLM instance is not ready or is "
                            f"not serving vLLM at {url}."
                        ) from exc
                    raise
            payload = response.json()

        choices = payload.get("choices") or []
        if not choices:
            raise ValueError(f"Model {self.model} returned no choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            message = {**message, "content": self._clean_content(content)}
        return message

    async def generate_text(self, prompt: str) -> str:
        message = await self.chat([{"role": "user", "content": prompt}])
        text = message.get("content")
        if not text:
            raise ValueError(f"Model {self.model} returned empty response")
        return str(text)

    async def generate_json_text(self, prompt: str) -> str:
        """Generate text while requesting a single JSON object when supported."""
        message = await self.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a JSON API. Return exactly one valid JSON object. "
                        "Do not include markdown, explanations, or text outside JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
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
        try:
            response = await client.post(url, headers=headers, json=body)
        except httpx.ConnectError as exc:
            raise RuntimeError(
                "Could not connect to the configured local LLM endpoint "
                f"{url}. Check LLM_BASE_URL and confirm the vLLM server is reachable."
            ) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                "Timed out while connecting to the configured local LLM endpoint "
                f"{url}. Increase LLM_TIMEOUT_SECONDS or check the vLLM server."
            ) from exc
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

    @staticmethod
    def _is_json_mode_error(response: httpx.Response) -> bool:
        if response.status_code not in {400, 422}:
            return False
        text = response.text.lower()
        return any(
            phrase in text
            for phrase in (
                "response_format",
                "json_object",
                "guided json",
                "json mode",
            )
        )

    @staticmethod
    def _clean_content(text: str) -> str:
        """Normalize common local-model decoding artifacts before parsing."""
        text = text.replace("\u0120", " ").replace("\u010a", "\n")
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"^.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
        return text.strip()
