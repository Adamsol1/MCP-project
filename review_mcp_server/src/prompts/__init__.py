"""Review MCP Server — Prompts package."""

from .analysis import analysis_review
from .collection import collection_review
from .direction import direction_review
from .processing import processing_review


def register_prompts(mcp) -> None:
    mcp.prompt(direction_review)
    mcp.prompt(collection_review)
    mcp.prompt(processing_review)
    mcp.prompt(analysis_review)
