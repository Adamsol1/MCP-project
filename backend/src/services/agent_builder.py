"""Generic agent builder for perspective-based analysis and council phases.

Fetches persona content from the knowledge bank via MCP Resources and
builds a participant dict ready for use in deliberation or analysis.
"""

from src.mcp_client.client import MCPClient
from src.models.dialogue import Perspective

_DISPLAY_NAMES: dict[Perspective, str] = {
    Perspective.US: "US Strategic Analyst",
    Perspective.NORWAY: "Norway Security Analyst",
    Perspective.CHINA: "China Strategic Analyst",
    Perspective.EU: "EU Policy Analyst",
    Perspective.RUSSIA: "Russia Strategic Analyst",
    Perspective.NEUTRAL: "Neutral Evidence Analyst",
}


def get_display_name(perspective: Perspective) -> str:
    return _DISPLAY_NAMES[perspective]


async def build_agent(
    mcp_client: MCPClient,
    perspective: Perspective,
    cli: str,
    model: str,
) -> dict:
    """Build a participant dict for a given perspective.

    Fetches the persona from knowledge://personas/{perspective} via MCP,
    then returns a dict suitable for passing to the deliberation engine
    or an analysis agent runner.

    Args:
        mcp_client: Connected MCPClient instance.
        perspective: The perspective to build an agent for.
        cli:         CLI adapter name (e.g. "gemini").
        model:       Model identifier (e.g. "gemini-2.5-flash").

    Returns:
        Dict with keys: cli, model, display_name, persona_prompt.
    """
    persona_prompt = await mcp_client.read_resource(
        f"knowledge://personas/{perspective.value}"
    )
    return {
        "cli": cli,
        "model": model,
        "display_name": get_display_name(perspective),
        "persona_prompt": persona_prompt,
    }
