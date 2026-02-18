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
def dialogue_question(user_message, missing_fields, perspectives, context) -> dict:
    """
    Docstring for dialogue_question
    Args:
        user_message : The user's input. e.g "Investigate APT29"
        missing_fields: List of context fields that misses information. e.g (["scope", "timeframe"])
        perspectives: List of selected viewpoints of the investigation. e.g ["neutral", "us"]
        context: Include context to give the tool enough information to ask context based questions instead of general questions.

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
        "has_sufficient_context" : True,
        "context" : context
    }
    if missing_fields:
        dialogue_question["has_sufficient_context"] = False

    return dialogue_question

@mcp.tool
def generate_pir(scope, timeframe, target_entities, perspectives, modifications=None) -> str:
    """
    Create a PIR based on investigation scope, timeframe and target entites gathered from dialogue.

    Args:
        scope: The focus area of the investigation. e.g. "identify attack patterns"
        timeframe: The time period the PIR covers. e.g. "last 6 months"
        target_entities: The entities relevant to the investigation. e.g. "NATO member states"
        perspectives: The selected viewpoints for the investigation. e.g. ["norway", "neutral"]
        modifications: Optional user feedback for regenerating the PIR. e.g. "Add focus on supply chain attacks"

    Returns:
        str: The formatted PIR

    Raises:
        ValueError: If scope, timeframe, or target_entities is missing
    """
    #Checks for required context. Return ValueError if not present
    if not scope:
        raise ValueError("scope is required")
    if not timeframe:
        raise ValueError("timeframe is required")
    if not target_entities:
        raise ValueError("target_entities is required")
    if not perspectives:
        perspectives = ["neutral"]


    return "test data"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
