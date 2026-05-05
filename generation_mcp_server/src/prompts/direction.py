"""Direction phase prompt builders and MCP adapter functions."""

import json

from ._shared import _language_instruction


def build_direction_dialogue_prompt(
    user_message: str,
    missing_fields: list,
    perspectives: list,
    context,
    language: str = "en",
) -> str:
    """Build prompt for direction phase dialogue question generation.

    Args:
        user_message: The user's latest input.
        missing_fields: Context fields that still lack values, e.g. ["scope", "timeframe"].
        perspectives: Selected analytical viewpoints, e.g. ["neutral", "norway"].
        context: Current dialogue context (dict with scope, timeframe, etc.).
        language: BCP-47 language code controlling which language the question is written in.

    Returns:
        Formatted prompt string ready to send to the AI model.
    """
    lang_instruction = _language_instruction(language, 'the "question" field')

    return (
        lang_instruction
        + f"""SYSTEM_PROMPT
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
                - If the user's message is unrelated to the intelligence task, politely
                redirect them back to the dialogue, do not update any context fields,
                and return the existing context unchanged

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
                - Set to true ONLY when ALL of the following fields have values:
                scope, target_entities, threat_actors, timeframe, priority_focus
                - Set to false if ANY of these fields is empty or an empty list

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

                USER_PROMPT ==
                The user has provided the following message:
                USER MESSAGE: {user_message}

                CURRENT CONTEXT (what we know so far):
                {context}

                SELECTED PERSPECTIVES: {perspectives}

                MISSING FIELDS: {missing_fields}
                """
    )


def build_pir_generation_prompt(
    scope: str,
    timeframe: str,
    target_entities: list,
    perspectives: list,
    threat_actors: list,
    priority_focus: str,
    modifications: str | None = None,
    current_pir: str | None = None,
    language: str = "en",
    background_knowledge: str | None = None,
) -> str:
    """Build prompt for PIR document generation.

    Args:
        scope: The focus area of the investigation.
        timeframe: The time period the PIR covers.
        target_entities: The entities relevant to the investigation.
        perspectives: The selected analytical viewpoints.
        threat_actors: The threat actors of interest.
        priority_focus: The main aspect to emphasize.
        modifications: Optional user feedback for regenerating the PIR.
        language: BCP-47 language code controlling which language the PIR is written in.
        background_knowledge: Optional additional knowledge to incorporate into the PIR generation.

    Returns:
        Formatted prompt string ready to send to the AI model.
    """
    lang_instruction = _language_instruction(
        language, "all PIR content (question, rationale, result, reasoning)"
    )

    return (
        lang_instruction
        + f"""SYSTEM_PROMPT
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

CITATION RULES (only apply if BACKGROUND KNOWLEDGE is provided below.
If BACKGROUND KNOWLEDGE is absent or empty, skip all citation rules
and return empty arrays for "sources" and "claims"):
- Build a top-level "sources" list from the "### Source: <id>" headers in the
  background knowledge. Each entry must have:
    {{ "id": "<source id>", "ref": "[N]", "source_type": "kb" }}
  where N is the 1-based position of the source in the sources list.
- In "pir_text", insert [N] superscript markers inline after any claim that is
  directly supported by a source. Example: "Russia has GPS jamming capability[1]"
- When a claim is supported by multiple sources, write consecutive separate markers
  with no space between them: "claim text[1][2]". Never combine as "[1,2]".
- For every [N] marker in pir_text, add a matching entry to "claims":
    {{ "id": "claim_<N>", "text": "<claim text without the marker>",
      "source_ref": "[N]", "source_id": "<matching source id>" }}
- Only insert [N] markers in pir_text. Do NOT insert [N] markers inside pir items'
  question or rationale fields — link pir items to sources via source_ids only.
- In each PIR item, set "source_ids" to a list of source IDs (not refs) that
  support that PIR. Use [] if no background knowledge applies.
- Only cite sources that genuinely influenced the content — do not fabricate links.
- Sentences with no verifiable source get no [N] marker and no claims entry.

ANALYTICAL PERSPECTIVES define the lens through which PIRs are framed:
- Single or multiple countries/groups (e.g. "norway", "russia", "nato"):
  Emulate the values and interests of the given entities to ensure PIRs
  are relevant to all selected perspectives collectively
- "neutral": Frame PIRs without bias toward any specific actor or nation
- Generate a single unified set of PIRs that is meaningful and applicable
  across all selected perspectives

Return your response in the following JSON format:
{{
    "pir_text": "A concise human-readable summary of what the PIRs collectively aim to answer. Insert [N] markers inline after any claim supported by background knowledge.",
    "claims": [
        {{
            "id": "claim_1",
            "text": "The claim text without the [N] marker",
            "source_ref": "[1]",
            "source_id": "geopolitical/norway_russia"
        }}
    ],
    "sources": [
        {{
            "id": "geopolitical/norway_russia",
            "ref": "[1]",
            "source_type": "kb"
        }}
    ],
    "pirs": [
        {{
            "question": "The PIR formulated as a specific intelligence question",
            "priority": "high | medium | low",
            "rationale": "Why this PIR is important given the context",
            "source_ids": ["geopolitical/norway_russia"]
        }}
    ],
    "reasoning": "A transparent explanation of the logic and decisions behind why these specific PIRs were selected"
}}

The "pirs" list MUST be sorted by priority order: high first, then medium, then low.

Respond ONLY in valid JSON.
No markdown.
No commentary.

USER_PROMPT
Generate PIRs for the following intelligence investigation:

SCOPE: {scope}
TIMEFRAME: {timeframe}
TARGET ENTITIES: {target_entities}
THREAT ACTORS: {threat_actors}
PRIORITY FOCUS: {priority_focus}
ANALYTICAL PERSPECTIVES: {perspectives}

EXISTING PIRs: {current_pir or "None"}
MODIFICATIONS: {modifications or "None"}
NOTE: A MODIFICATIONS value of "None" means no feedback has been provided.
Do not treat "None" as feedback content.
{background_knowledge or ""}

Use the following rules to decide how to respond:
- If MODIFICATIONS is "None": Generate a fresh set of 2-5 PIRs based
  on the investigation context above.
- If MODIFICATIONS has content and EXISTING PIRs is not None:
  - First, classify the feedback into one of three types:
    1. Additive (e.g. "add a PIR about X", "include a PIR on Y", "add one about Z"):
       Keep ALL existing PIRs completely unchanged and append only the new PIR(s)
       to the list. Do not modify, merge, reword, or remove any existing PIRs.
    2. Specific (e.g. "change PIR 2", "PIR 3 is too vague", "rewrite PIR 1"):
       Keep all other PIRs unchanged and only modify the ones explicitly mentioned.
    3. General (e.g. "poor quality", "too broad", "not relevant enough"):
       Regenerate all PIRs from scratch, using the feedback as quality guidance.
- If MODIFICATIONS has content but EXISTING PIRs is None: Regenerate
  PIRs from scratch, but take the requested changes into account as
  additional constraints.
"""
    )


def build_direction_summary_prompt(
    scope: str,
    timeframe: str,
    target_entities: list,
    threat_actors: list,
    priority_focus: str,
    perspectives: list,
    modifications: str | None = None,
    language: str = "en",
) -> str:
    """Build prompt for intelligence context summary generation.

    Args:
        scope: The focus area of the investigation.
        timeframe: The time period of the investigation.
        target_entities: The entities relevant to the investigation.
        threat_actors: The threat actors of interest.
        priority_focus: The main aspect to emphasize.
        perspectives: The selected analytical viewpoints.
        modifications: Optional user feedback to incorporate into the summary.
        language: BCP-47 language code controlling which language the summary is written in.

    Returns:
        Formatted prompt string ready to send to the AI model.
    """
    lang_instruction = _language_instruction(language, "the summary")

    return (
        lang_instruction
        + f"""SYSTEM_PROMPT
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

USER_PROMPT
Summarise the following intelligence investigation context:

SCOPE: {scope}
TIMEFRAME: {timeframe}
TARGET ENTITIES: {target_entities}
THREAT ACTORS: {threat_actors}
PRIORITY FOCUS: {priority_focus}
ANALYTICAL PERSPECTIVES: {perspectives}

MODIFICATIONS: {modifications or "None"}
NOTE: A MODIFICATIONS value of "None" means no feedback has been provided.
Do not treat "None" as feedback content.
- If MODIFICATIONS is "None": summarise the context as-is.
- If MODIFICATIONS has content: incorporate the requested changes into the summary.
"""
    )


# ── MCP adapter functions ─────────────────────────────────────────────────────


def direction_gathering(
    user_message: str,
    missing_fields: str,
    context: str,
    language: str = "en",
) -> str:
    """Prompt for generating a clarifying question in the Direction dialogue phase."""
    ctx = json.loads(context)
    return build_direction_dialogue_prompt(
        user_message=user_message,
        missing_fields=json.loads(missing_fields),
        perspectives=ctx.get("perspectives", []),
        context=ctx,
        language=language,
    )


def direction_summary(
    scope: str,
    timeframe: str,
    target_entities: str,
    threat_actors: str,
    priority_focus: str,
    perspectives: str,
    modifications: str = "",
    language: str = "en",
) -> str:
    """Prompt for generating a context summary in the Direction phase.

    Args:
        scope: The focus area of the investigation.
        timeframe: The time period of the investigation.
        target_entities: JSON array of relevant entities.
        threat_actors: JSON array of threat actors.
        priority_focus: The main aspect to emphasize.
        perspectives: JSON array of selected perspectives.
        modifications: Optional user feedback to incorporate.
        language: BCP-47 language code.
    """
    return build_direction_summary_prompt(
        scope=scope,
        timeframe=timeframe,
        target_entities=json.loads(target_entities),
        threat_actors=json.loads(threat_actors),
        priority_focus=priority_focus,
        perspectives=json.loads(perspectives),
        modifications=modifications or None,
        language=language,
    )


def direction_pir(
    scope: str,
    timeframe: str,
    target_entities: str,
    threat_actors: str,
    priority_focus: str,
    perspectives: str,
    modifications: str = "",
    current_pir: str = "",
    language: str = "en",
    background_knowledge: str = "",
) -> str:
    """Prompt for generating PIRs from gathered dialogue context."""
    return build_pir_generation_prompt(
        scope=scope,
        timeframe=timeframe,
        target_entities=json.loads(target_entities),
        threat_actors=json.loads(threat_actors),
        priority_focus=priority_focus,
        perspectives=json.loads(perspectives),
        modifications=modifications or None,
        current_pir=current_pir or None,
        language=language,
        background_knowledge=background_knowledge or None,
    )
