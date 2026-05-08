"""Provider registry — single switch point for picking an LLM backend.

`get_provider()` honors any active `request_llm_provider` override, so a
per-request `ai_provider` field on the API can swap providers without
reconfiguring the process.
"""

from __future__ import annotations

from src.services.ai.llm_config import get_llm_provider
from src.services.ai.providers.base import LLMProvider, ToolAgent
from src.services.ai.providers.gemini import GeminiProvider
from src.services.ai.providers.openai_compat import OpenAICompatibleProvider


def get_provider(model: str | None = None) -> LLMProvider:
    """Return the LLMProvider for the currently active backend.

    Args:
        model: Optional override for the model id. When omitted, each
               provider falls back to its env-configured default.
    """
    provider_name = get_llm_provider()
    if provider_name == "gemini":
        return GeminiProvider(model=model)
    return OpenAICompatibleProvider(model=model)


__all__ = [
    "LLMProvider",
    "ToolAgent",
    "GeminiProvider",
    "OpenAICompatibleProvider",
    "get_provider",
]
