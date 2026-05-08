"""Thin facade over `providers.get_provider().tool_agent(...)`.

Kept as a separate module because every phase service imports
`create_tool_agent`. The provider switch lives in `providers/`.
"""

from src.services.ai.providers import get_provider


def create_tool_agent(
    mcp_client,
    model: str | None = None,
    max_tool_rounds: int = 50,
):
    """Return the active provider's MCP tool-loop agent."""
    return get_provider(model=model).tool_agent(
        mcp_client,
        max_tool_rounds=max_tool_rounds,
    )
