"""MCP Threat Intelligence Server.

This server provides tools, resources, and prompts for the
Threat Intelligence workflow (Direction, Collection, Processing phases).
"""

import json
import os
from sys import stderr

from dotenv import load_dotenv
from fastmcp import FastMCP
from google import genai

from prompts import (
    build_direction_dialogue_prompt,
    build_pir_generation_prompt,
    build_summary_prompt,
    COLLECTION_REVIEW_PROMPT,
    DIRECTION_REVIEW_PROMPT,
    PROCESSING_REVIEW_PROMPT,
)

load_dotenv()

print("Starting MCP Threat Intelligence Server...", file=stderr, flush=True)

api_key = os.getenv("GEMINI_API_KEY")
print(f"API KEY FOUND: {bool(api_key)}", file=stderr, flush=True)

client = genai.Client(api_key=api_key)

mcp = FastMCP(
    name="ThreatIntelligence",
    instructions="MCP server for Threat Intelligence workflow assistance.",
)


@mcp.tool
def greet() -> str:
    """Test tool to verify the server is running."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say hello, say what model you are, and mentiond todays' date if you can. Also answer 2+2",
    )

    return f"Hello, this is the MCP Threat Intelligence server! Gemini Response: {response.text}"

#Tool for generating questions.
@mcp.tool
def dialogue_question(user_message, missing_fields, perspectives, context, language="en") -> dict:
    """
    Generate a clarifying question based on user input and current context.

    Args:
        user_message : The user's input. e.g "Investigate APT29"
        missing_fields: List of context fields that misses information. e.g (["scope", "timeframe"])
        perspectives: List of selected viewpoints of the investigation. e.g ["neutral", "us"]
        context: Include context to give the tool enough information to ask context based questions instead of general questions.
        language: BCP-47 language code for the response language. e.g "en" (English), "no" (Norwegian).

    Returns:
        dict with:
            Question (str): The clarifying question to ask the user
            type (str): What context the question targets. Based on QuestionType in backend/models/dialogue.py. Possible question types : [scope, timeframe, target_entities, actors, focus, confirmation]
            has_sufficient_context (bool). Wether all context is filled or not. True if no more question needed. False if more questions needed to fill all context.
            context. what we know so far.

            Example:
                dialogue_question = {
                    "question" : "identify attack patterns",
                    "type" : "scope",
                    "has_sufficient_context" : False,
                    ""context": {{
                        "scope": "extracted or existing value, empty string if unknown",
                        "timeframe": "extracted or existing value, empty string if unknown",
                        "target_entities": ["list", "or", "empty"],
                        "threat_actors": ["list", "or", "empty"],
                        "priority_focus": "extracted or existing value, empty string if unknown",
                        "perspectives": ["list", "or", "empty"]
                    }}
                }

    """

    if not perspectives:
        perspectives = ["neutral"]
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_direction_dialogue_prompt(user_message, missing_fields, perspectives, context, language),
    )
    #Check for faulty response
    if not response.text:
            raise ValueError("Gemini returned emtpy response")

    try:
        result = json.loads(response.text)


    except json.JSONDecodeError as e:
        print("Ai did not return valid JSON", e, file=stderr, flush=True)
        raise


    # Backend override: if we know fields are missing, force False regardless of AI judgement
    if missing_fields:
        result["has_sufficient_context"] = False
    return result

@mcp.tool
def generate_pir(scope, timeframe, target_entities, perspectives, threat_actors, priority_focus, modifications=None, language="en") -> str:
    """
    Create a PIR based on investigation scope, timeframe and target entites gathered from dialogue.

    Args:
        scope: The focus area of the investigation. e.g. "identify attack patterns"
        timeframe: The time period the PIR covers. e.g. "last 6 months"
        target_entities: The entities relevant to the investigation. e.g. "NATO member states"
        perspectives: The selected viewpoints for the investigation. e.g. ["norway", "neutral"]
        modifications: Optional user feedback for regenerating the PIR. e.g. "Add focus on supply chain attacks"
        language: BCP-47 language code for the response language. e.g "en" (English), "no" (Norwegian).

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

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_pir_generation_prompt(scope, timeframe, target_entities, perspectives, threat_actors, priority_focus, modifications, language),
    )

    #Return the JSON
    return response.text





@mcp.tool
def generate_summary(scope, timeframe, target_entities, threat_actors, priority_focus, perspectives, modifications=None, language="en") -> str:
    """
    Generate a human-readable summary of the gathered intelligence context.

    Args:
        scope: The focus area of the investigation.
        timeframe: The time period of the investigation.
        target_entities: The entities relevant to the investigation.
        threat_actors: The threat actors of interest.
        priority_focus: The main aspect to emphasize.
        perspectives: The selected analytical viewpoints.
        modifications: Optional user feedback to incorporate into the summary.
        language: BCP-47 language code for the response language. e.g "en" (English), "no" (Norwegian).

    Returns:
        str: JSON with a 'summary' field containing a human-readable summary.
    """
    if not perspectives:
        perspectives = ["neutral"]

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_summary_prompt(scope, timeframe, target_entities, threat_actors, priority_focus, perspectives, modifications, language),
    )

    return response.text

@mcp.tool
def review(content, context, phase) -> str:
    """Review generated content against the dialogue context for a given intelligence cycle phase.

    Args:
        content: The generated content to review (e.g. a set of PIRs).
        context: The dialogue context used during generation (dict).
        phase: The intelligence cycle phase being reviewed.
                Valid values: "direction", "collection", "processing".

    Returns:
        JSON string with overall_approved (bool), severity ("none" | "minor" | "major"),
        pir_reviews (list) and suggestions (str | null).

    Raises:
        KeyError: If phase is not a recognised value.
    """
    # Dispatch to the correct review prompt based on the current intelligence cycle phase
    prompts = {
        "direction": DIRECTION_REVIEW_PROMPT,
        "collection": COLLECTION_REVIEW_PROMPT,
        "processing": PROCESSING_REVIEW_PROMPT,
    }
    prompt = prompts[phase]

    response = client.models.generate_content(
        model = "gemini-2.5-flash",
        contents = prompt(content, context)
    )

    return response.text



if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False, log_level="ERROR")
