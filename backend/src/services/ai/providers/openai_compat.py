"""OpenAICompatibleProvider — covers vLLM, Ollama, LM Studio, DeepSeek, OpenAI, etc.

Any backend that speaks the OpenAI `/chat/completions` shape goes through this
provider. Per-model quirks (e.g. Qwen's `chat_template_kwargs.enable_thinking`)
already live in the underlying client and only fire when the user opts in via
`LLM_ENABLE_THINKING`.
"""

from __future__ import annotations

from typing import Any

from src.services.ai.llm_config import LLMConfig, get_llm_config
from src.services.ai.openai_compatible_client import OpenAICompatibleClient
from src.services.ai.tool_calling_agent import ToolCallingAgent


class OpenAICompatibleProvider:
    name = "local"

    def __init__(
        self,
        model: str | None = None,
        config: LLMConfig | None = None,
    ):
        self._config = config or get_llm_config(model=model)
        self._client = OpenAICompatibleClient(config=self._config)
        self.model = self._client.model

    async def generate_text(self, prompt: str) -> str:
        return await self._client.generate_text(prompt)

    async def generate_json_text(self, prompt: str) -> str:
        return await self._client.generate_json_text(prompt)

    async def chat(self, messages: list[dict[str, Any]]) -> str:
        message = await self._client.chat(messages)
        text = message.get("content")
        if not text:
            raise ValueError(f"Model {self.model} returned empty response")
        return str(text)

    def tool_agent(
        self,
        mcp_client: Any,
        max_tool_rounds: int = 50,
    ) -> ToolCallingAgent:
        return ToolCallingAgent(
            mcp_client,
            model=self.model,
            max_tool_rounds=max_tool_rounds,
        )
