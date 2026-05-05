"""Processing phase MCP tools — analyst clarification for ambiguous categorisation."""

from fastmcp import Context


async def request_pmesii_clarification(
    ctx: Context,
    entity_name: str,
    candidate_categories: list[str],
    reasoning: str,
) -> str:
    """Ask the analyst to choose a PMESII category when the AI is uncertain.

    Call this tool when you cannot determine the best PMESII category for a
    finding on your own. The analyst will see the finding name, the two
    candidate categories, and your reasoning, and will select the correct one.

    Args:
        entity_name:          The title of the finding being categorised.
        candidate_categories: Exactly two PMESII categories to choose between.
        reasoning:            One sentence explaining why both categories could apply.

    Returns:
        The analyst's chosen category string, or "cancelled" if declined.
    """
    result = await ctx.elicit(
        message=(
            f'Uncertain PMESII categorisation for "{entity_name}". {reasoning}'
        ),
        response_type=candidate_categories,
    )

    if hasattr(result, "data") and isinstance(result.data, str):
        return result.data
    return "cancelled"


def register_processing_tools(mcp) -> None:
    mcp.tool(request_pmesii_clarification)
