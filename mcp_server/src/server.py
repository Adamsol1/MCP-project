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
        contents=f"""SYSTEM_PROMPT
                You are an expert threat intelligence analyst conducting a structured
                intelligence requirements dialogue.

                Your job is to:
                1. Extract any intelligence context from the user's latest message
                2. Generate one smart follow-up question to fill the most
                important missing context

                EXTRACTION RULES:
                - Extract only what is explicitly or clearly implied in the user's message
                - Do not infer or assume values that are not stated
                - If a field is already filled in the existing context, do not overwrite
                it unless the user explicitly changes it

                QUESTION GENERATION RULES:
                - Ask only ONE question per response
                - If sufficient context exists: ask a specific, tailored question based
                on what you already know
                - If context is too vague: ask a broad but intelligent clarifying question
                that helps narrow down the most critical missing information
                - Prioritize the most critical missing field first
                - Use the selected perspectives to frame the question relevantly

                FIELD PRIORITY ORDER (if multiple fields are missing):
                1. scope — without this, nothing else makes sense
                2. target_entities — who/what is being investigated
                3. threat_actors — who is the adversary
                4. timeframe — when
                5. priority_focus — what aspect to emphasize
                6. perspectives — analytical viewpoint

                has_sufficient_context RULES:
                - Set to true only when ALL of the following fields have values:
                scope, target_entities, threat_actors, timeframe, priority_focus, perspectives
                - Set to true when context is good enough to generate meaningful PIRs
                — not when it is perfect. Intelligence analysts never have perfect information.
                - Set to false if ANY required field is empty

                Return your response in the following JSON format:
                {{
                    "question": "One specific or intelligently broad follow-up question",
                    "type": "the field this question targets e.g. target_entities",
                    "has_sufficient_context": true or false,
                    "context": {{
                        "scope": "extracted or existing value, empty string if unknown",
                        "timeframe": "extracted or existing value, empty string if unknown",
                        "target_entities": ["list", "or", "empty"],
                        "threat_actors": ["list", "or", "empty"],
                        "priority_focus": "extracted or existing value, empty string if unknown",
                        "perspectives": ["list", "or", "empty"]
                    }}
                }}
                Respond ONLY in valid JSON.
                No markdown.
                No commentary.
                If the user message is in Norwegian, write the "question" field in Norwegian.

                USER_PROMPT ==
                The user has provided the following message:
                USER MESSAGE: {user_message}

                CURRENT CONTEXT (what we know so far):
                {context}

                SELECTED PERSPECTIVES: {perspectives}

                MISSING FIELDS: {missing_fields}

                1. Extract any new context from the user message and update the context above
                2. Generate one follow-up question targeting the most critical missing field
                """
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
def generate_pir(scope, timeframe, target_entities, perspectives,threat_actors, priority_focus, modifications=None) -> str:
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


    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""SYSTEM_PROMPT
You are an expert threat intelligence analyst specializing in
creating Priority Intelligence Requirements (PIRs).

A PIR is a specific, measurable intelligence question that:
- Addresses a critical gap in the commander/decision-maker's understanding
- Directly supports a specific decision or action
- Is answerable within the given timeframe and scope
- Focuses on adversary capabilities, intentions, or opportunities

Your task is to generate 2-5 PIRs based on the investigation context
provided. Each PIR must be:
- Specific: Tied to the exact scope, entities, and timeframe given
- Measurable: Has a clear answer that can be found through collection
- Prioritized: Ranked by importance to the decision at hand
- Perspective-aware: Framed through the selected analytical viewpoint(s)

ANALYTICAL PERSPECTIVES define the lens through which PIRs are framed:
- Single or multiple countries/groups (e.g. "norway", "russia", "nato"):
  Emulate the values and interests of the given entities to ensure PIRs
  are relevant to all selected perspectives collectively
- "neutral": Frame PIRs without bias toward any specific actor or nation
- Generate a single unified set of PIRs that is meaningful and applicable
  across all selected perspectives

Return your response in the following JSON format:
{{
    "result": "A concise, human-readable summary of the generated PIRs and what they collectively aim to answer",
    "pirs": [
        {{
            "question": "The PIR formulated as a specific intelligence question",
            "priority": "high | medium | low",
            "rationale": "Why this PIR is important given the context"
        }}
    ],
    "reasoning": "A transparent explanation of the logic and decisions behind why these specific PIRs were selected"
}}
Respond ONLY in valid JSON.
No markdown.
No commentary.
If the MODIFICATIONS field is in Norwegian, write all PIR content (question, rationale, result, reasoning) in Norwegian. Otherwise write in English.

USER_PROMPT
Generate PIRs for the following intelligence investigation:

SCOPE: {scope}
TIMEFRAME: {timeframe}
TARGET ENTITIES: {target_entities}
THREAT ACTORS: {threat_actors}
PRIORITY FOCUS: {priority_focus}
ANALYTICAL PERSPECTIVES: {perspectives}

MODIFICATIONS: {modifications}
- If MODIFICATIONS is empty: Generate a fresh set of 2-5 PIRs based
  on the investigation context above.
- If MODIFICATIONS has content: Regenerate the PIRs from scratch,
  but take the requested changes into account as additional constraints.
"""
    )

    #Return the JSON
    return response.text





@mcp.tool
def generate_summary(scope, timeframe, target_entities, threat_actors, priority_focus, perspectives, modifications=None) -> str:
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

    Returns:
        str: JSON with a 'summary' field containing a human-readable summary.
    """
    if not perspectives:
        perspectives = ["neutral"]

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""SYSTEM_PROMPT
You are an expert threat intelligence analyst.
Your task is to produce a clear, concise summary of the intelligence
investigation context gathered so far.

The summary should:
- Be written in plain language a decision-maker can understand
- Reflect all context fields provided
- If MODIFICATIONS has content: acknowledge what the user wants changed
  and describe how it will affect the investigation

Return your response in the following JSON format:
{{
    "summary": "A clear, human-readable narrative summarising the investigation context and any requested modifications"
}}
Respond ONLY in valid JSON.
No markdown.
No commentary.
If MODIFICATIONS is in Norwegian, write the summary in Norwegian. Otherwise write in English.

USER_PROMPT
Summarise the following intelligence investigation context:

SCOPE: {scope}
TIMEFRAME: {timeframe}
TARGET ENTITIES: {target_entities}
THREAT ACTORS: {threat_actors}
PRIORITY FOCUS: {priority_focus}
ANALYTICAL PERSPECTIVES: {perspectives}

MODIFICATIONS: {modifications}
- If MODIFICATIONS is empty: summarise the context as-is.
- If MODIFICATIONS has content: incorporate the requested changes into the summary.
"""
    )

    return response.text
"""
@mcp.tool
def review(content, context, phase) -> str:
    prompts = {
        Phase.DIRECTION: DIRECTION_REVIEW_PROMPT,
        Phase.COLLECTION: COLLECTION_REVIEW_PROMPT,
        Phase.PROCESSING: PROCESSING_REVIEW_PROMPT,
    }
    prompt = prompts[phase]

    response = client.models.generate_content(
        model = "gemini-2.5-flash",
        contents = prompt
    )

    return response.text
"""


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False, log_level="ERROR")
