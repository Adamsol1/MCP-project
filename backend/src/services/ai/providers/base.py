"""LLMProvider — single abstraction the rest of the app talks to.

Every concrete provider (Gemini, OpenAI-compatible, …) implements this
interface so call sites never branch on provider name. Swapping in a new
backend (DeepSeek, Anthropic, OpenRouter, …) is one new file plus one line
in the registry.
"""

from __future__ import annotations

from typing import Any, Protocol


class ToolAgent(Protocol):
    """Duck-typed contract for the MCP tool-loop agent each provider returns."""

    last_thought_text: str

    async def run(
        self,
        system_prompt: str,
        task: str,
        allowed_tool_names: set[str] | None = None,
        status_tracker: Any = None,
        response_format: dict[str, Any] | None = None,
    ) -> str: ...


class LLMProvider(Protocol):
    """Interface for direct (non-tool) LLM calls and tool-agent construction.

    Implementations are constructed by `providers.get_provider()`. The
    `model` attribute is the resolved model id (after env / argument fallback)
    so callers can log it without re-resolving.
    """

    name: str
    model: str

    async def generate_text(self, prompt: str) -> str:
        """Single-prompt completion. Returns the raw text response."""
        ...

    async def generate_json_text(self, prompt: str) -> str:
        """Same as `generate_text` but the prompt asks for JSON.

        Implementations may set provider-specific JSON-mode flags
        (e.g. `response_format={"type": "json_object"}` for OpenAI-compatible
        endpoints, `response_mime_type` for Gemini).
        """
        ...

    async def chat(self, messages: list[dict[str, Any]]) -> str:
        """Multi-turn chat. `messages` is OpenAI-style `[{role, content}, ...]`.

        Providers that don't natively use that shape (e.g. Gemini) translate
        internally so callers stay format-agnostic.
        """
        ...

    def tool_agent(
        self,
        mcp_client: Any,
        max_tool_rounds: int = 50,
    ) -> ToolAgent:
        """Return the provider's MCP tool-loop agent."""
        ...
