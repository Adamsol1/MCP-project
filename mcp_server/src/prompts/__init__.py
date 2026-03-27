"""MCP Prompts package."""

from ._shared import SOURCE_TOOL_MAP, _language_instruction
from .collection import (
    build_collection_collect_prompt,
    build_collection_modify_prompt,
    build_collection_plan_prompt,
    build_collection_summarize_prompt,
    collection_collect,
    collection_modify,
    collection_plan,
    collection_summarize,
)
from .direction import (
    build_direction_dialogue_prompt,
    build_direction_summary_prompt,
    build_pir_generation_prompt,
    direction_gathering,
    direction_pir,
    direction_summary,
)


def register_prompts(mcp) -> None:
    mcp.prompt(direction_gathering)
    mcp.prompt(direction_summary)
    mcp.prompt(direction_pir)
    mcp.prompt(collection_plan)
    mcp.prompt(collection_collect)
    mcp.prompt(collection_summarize)
    mcp.prompt(collection_modify)
