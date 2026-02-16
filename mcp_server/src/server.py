"""MCP Threat Intelligence Server.

This server provides tools, resources, and prompts for the
Threat Intelligence workflow (Direction, Collection, Processing phases).
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="ThreatIntelligence",
    instructions="MCP server for Threat Intelligence workflow assistance.",
)


@mcp.tool
def greet() -> str:
    """Test tool to verify the server is running."""
    return "Hello, this is the MCP Threat Intelligence server!"

#Tool for generating questions.
@mcp.tool
def dialogue_question(user_message, missing_fields, perspectives) -> dict:
    """
    Args:
        user_message : The user's input. e.g "Investigate APT29"
        Missing_fields: List of context fields that misses information. e.g (["scope", "timeframe"])
        Perspectives: List of selected viewpoints of the investigation. e.g ["neutral", "us"]

    Returns:
        dict with:
            Question (str): The clarifying question to ask the user
            type (str): What context the question targets. Based on QuestionType in backend/models/dialogue.py. Possible question types : [scope, timeframe, target_entities, actors, focus, confirmation]
            has_sufficient_context (bool). Wether all context is filled or not. True if no more question needed. False if more questions needed to fill all context.

            Example:
                dialogue_question = {
                    "question" : "identify attack patterns",
                    "type" : "scope",
                    "has_sufficient_context" : False
                }

    """
    #temp return
    dialogue_question = {
        "question" : "identify attack patterns",
        "type" : "scope",
        "has_sufficient_context" : True
    }
    if missing_fields:
        dialogue_question["has_sufficient_context"] = False

    return dialogue_question

@mcp.tool
def generate_pir(scope, timeframe, target_entities) -> str:
    return "test data"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
