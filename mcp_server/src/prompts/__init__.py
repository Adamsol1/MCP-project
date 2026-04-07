"""MCP Prompts package."""

from .collection import (
    collection_collect,
    collection_modify,
    collection_plan,
    collection_summarize,
)
from .direction import direction_gathering, direction_pir, direction_summary
from .processing import processing_modify, processing_process


def register_prompts(mcp) -> None:
    mcp.prompt(direction_gathering)
    mcp.prompt(direction_summary)
    mcp.prompt(direction_pir)
    mcp.prompt(collection_plan)
    mcp.prompt(collection_collect)
    mcp.prompt(collection_summarize)
    mcp.prompt(collection_modify)
    mcp.prompt(processing_process)
    mcp.prompt(processing_modify)
