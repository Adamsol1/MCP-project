"""Prompt builders for the Direction phase of the intelligence cycle.

All AI calls in the Direction phase go directly through LLMService —
no MCP involvement. These prompts are used by DialogueService and ReviewService.
"""

_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "no": "Norwegian",
}


def _language_instruction(language: str, scope: str = "all output") -> str:
    language_name = _LANGUAGE_NAMES.get(language, "English")
    return f"LANGUAGE INSTRUCTION: You MUST write {scope} in {language_name}.\n\n"


def build_direction_dialogue_prompt(
    user_message: str,
    missing_fields: list,
    perspectives: list,
    context,
    language: str = "en",
) -> str:
    """Build prompt for direction phase dialogue question generation."""
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
    """Build prompt for PIR document generation."""
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

CITATION RULES (apply when BACKGROUND KNOWLEDGE is present):
- Use the provided background knowledge to inform and ground your PIRs
- For each PIR, populate "sources" with a list of file paths from the
  "### Source:" headers that directly support that PIR
- Only cite a source if it genuinely influenced that specific PIR
- Use an empty list [] if no background knowledge applies to a PIR
- In the "reasoning" field, cite sources inline using [N] markers (e.g. [1], [2])
  where N corresponds to the 1-based index of the source in the flat list of all
  unique sources across all PIRs (ordered by first appearance)

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
            "rationale": "Why this PIR is important given the context",
            "sources": ["knowledge_bank/geopolitical/norway_russia.md"]
        }}
    ],
    "reasoning": "A transparent explanation of the logic and decisions behind why these specific PIRs were selected. When background knowledge is present, cite sources inline with [N] markers."
}}
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
MODIFICATIONS: {modifications}
{background_knowledge or ""}

Use the following rules to decide how to respond:
- If MODIFICATIONS is empty: Generate a fresh set of 2-5 PIRs based
  on the investigation context above.
- If MODIFICATIONS has content and EXISTING PIRs is not None:
  - First, judge whether the feedback targets specific PIRs (e.g. "change PIR 2",
    "PIR 3 is too vague") or is general (e.g. "poor quality", "too broad",
    "not relevant enough").
  - Specific feedback: keep all other PIRs unchanged and only modify the ones
    explicitly mentioned.
  - General feedback: regenerate all PIRs from scratch, using the feedback
    as quality guidance.
- If MODIFICATIONS has content but EXISTING PIRs is None: Regenerate
  PIRs from scratch, but take the requested changes into account as
  additional constraints.
"""
    )


def build_summary_prompt(
    scope: str,
    timeframe: str,
    target_entities: list,
    threat_actors: list,
    priority_focus: str,
    perspectives: list,
    modifications: str | None = None,
    language: str = "en",
) -> str:
    """Build prompt for intelligence context summary generation."""
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

MODIFICATIONS: {modifications}
- If MODIFICATIONS is empty: summarise the context as-is.
- If MODIFICATIONS has content: incorporate the requested changes into the summary.
"""
    )


def build_direction_review_prompt(content, context) -> str:
    """Build review prompt for PIRs generated in the Direction phase."""
    return f"""
You are a strict quality reviewer for Priority Intelligence Requirements (PIRs)
generated in the Direction phase of a threat intelligence cycle.

Your role is to ensure PIRs meet professional intelligence standards before
they are presented to the analyst. You are NOT a grammar checker — you
evaluate substance, relevance, and analytical quality.

You will receive:
- CONTEXT: The analyst's intelligence problem and dialogue: {context}
- Content: The generated PIRs to review: {content}

## Review each PIR against these criteria:

### 1. SMART criteria
- Specific: One clear intelligence need, preferably in a single sentence
- Measurable: It must be possible to determine when the requirement is fulfilled
- Realistic: Achievable given realistic collection capabilities
- Timely: Deadline or time scope must be clearly stated

### 2. Decision support
Does this PIR directly support a concrete decision stated or implied in the context?
A PIR that is "interesting" but does not enable a decision must be rejected.

### 3. Knowledge gap
Does this PIR address a real gap in understanding — not something already
known or trivially answerable? "Nice to know" is not enough.

### 4. Answers the actual problem
Compare each PIR against the analyst's original intelligence problem in CONTEXT.
A technically correct PIR that answers the wrong question must be rejected.

### 5. Number of PIRs
The set should contain 2-5 PIRs. Flag if:
- Only 1 PIR: likely too narrow or the problem is underdefined
- More than 5 PIRs: likely too broad or poorly prioritized

## Severity threshold
This is the Direction phase — poor PIRs propagate errors through the entire
intelligence cycle. When in doubt, mark as MAJOR.

- MAJOR: Missing one or more criteria, or PIR answers wrong question
- MINOR: Correct substance but could be more precise in formulation

## Output
Return valid JSON only. No explanation outside the JSON.
No markdown.
No code fences.

{{
  "overall_approved": bool,
  "severity": "none" | "minor" | "major",
  "pir_reviews": [
    {{
      "pir_index": int,
      "approved": bool,
      "issue": "string or null"
    }}
  ],
  "suggestions": "string or null"
}}

"""
