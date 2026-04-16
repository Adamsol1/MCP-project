from .personas import (
    council_persona_china,
    council_persona_eu,
    council_persona_neutral,
    council_persona_norway,
    council_persona_russia,
    council_persona_us,
)


def register_prompts(mcp) -> None:
    mcp.prompt(council_persona_us)
    mcp.prompt(council_persona_norway)
    mcp.prompt(council_persona_china)
    mcp.prompt(council_persona_eu)
    mcp.prompt(council_persona_russia)
    mcp.prompt(council_persona_neutral)
