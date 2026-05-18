"""Review MCP Server — Prompts package."""

from .analysis import analysis_review
from .collection import collection_review
from .direction import direction_review
from .processing import processing_review


def register_prompts(mcp) -> None:
    """Attach each phase's review prompt to the given FastMCP instance.

    Ordering follows the intelligence cycle (Direction, Collection, Processing,
    Analysis). The order is cosmetic since prompts are addressed by name, but
    keeping it consistent makes MCP discovery output easier to scan.
    """
    mcp.prompt(direction_review)
    mcp.prompt(collection_review)
    mcp.prompt(processing_review)
    mcp.prompt(analysis_review)
