"""Factory for provider-specific MCP tool-loop agents."""

from src.services.llm_config import get_default_gemini_model, get_llm_provider
from src.services.tool_calling_agent import ToolCallingAgent


def create_tool_agent(
    mcp_client,
    model: str | None = None,
    max_tool_rounds: int = 50,
):
    """Create the active provider's tool-calling agent.

    Gemini uses the Google Gemini function-calling API. Local uses the
    OpenAI-compatible endpoint configured by LLM_BASE_URL/LLM_MODEL.
    """

    if get_llm_provider() == "gemini":
        from src.services.gemini_agent import GeminiAgent

        return GeminiAgent(
            mcp_client,
            model=model or get_default_gemini_model(),
            max_tool_rounds=max_tool_rounds,
        )

    return ToolCallingAgent(
        mcp_client,
        model=model,
        max_tool_rounds=max_tool_rounds,
    )
