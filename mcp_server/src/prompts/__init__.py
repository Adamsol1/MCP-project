"""MCP Prompts - Workflow templates."""

from datetime import UTC, datetime

# Maps BCP-47 language codes to human-readable names used in language instructions.
_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "no": "Norwegian",
}

# Maps human-readable source names (as shown in the UI) to their MCP tool names.
SOURCE_TOOL_MAP: dict[str, list[str]] = {
    "Internal Knowledge Bank": ["list_knowledge_base", "read_knowledge_base"],
    "AlienVault OTX": ["query_otx"],
    # "MISP": ["search_misp"],  # MISP not configured on external server
    "Uploaded Documents": ["list_uploads", "search_local_data", "read_upload"],
    "Web Search": ["google_search", "google_news_search"],
}


def _language_instruction(language: str, scope: str = "all output") -> str:
    """Return a standardised language instruction line for prepending to prompts.

    Args:
        language: BCP-47 language code, e.g. "en" or "no".
        scope: Human-readable description of what must be in that language.

    Returns:
        A single instruction line ready to prepend to the prompt.
    """
    language_name = _LANGUAGE_NAMES.get(language, "English")
    return f"LANGUAGE INSTRUCTION: You MUST write {scope} in {language_name}.\n\n"


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

CITATION RULES (apply when BACKGROUND KNOWLEDGE is present):
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

MODIFICATIONS: {modifications}
- If MODIFICATIONS is empty: summarise the context as-is.
- If MODIFICATIONS has content: incorporate the requested changes into the summary.
"""
    )



def build_collection_modify_prompt(
    collected_data: str,
    modifications: str,
    language: str = "en",
) -> str:
    lang_note = _language_instruction(language, "the 'summary' and 'gaps' fields")

    return f"""You are a professional threat intelligence analyst. Apply the requested modification to an existing intelligence summary.

## Modification Request
{modifications}

## Existing Summary
{collected_data}

## Instructions
1. Apply only the requested changes — do not re-collect data or add new information
2. Preserve all content that was not mentioned in the modification request
3. Keep the same JSON structure as the existing summary

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown.

{{
  "summary": "The modified factual narrative",
  "sources_used": ["source1", "source2"],
  "gaps": "Updated gaps — or null if no gaps"
}}

{lang_note}"""


def build_collection_plan_prompt(
    pir: str,
    modifications: str | None = None,
    language: str = "en",
) -> str:
    available_sources = list(SOURCE_TOOL_MAP.keys())
    available_sources_str = ", ".join(f'"{s}"' for s in available_sources)
    lang_note = _language_instruction(language, "the 'plan' field")

    modifications_section = (
        f"\n## Modification Request\n{modifications}\nIncorporate this change into the plan."
        if modifications else ""
    )

    return f"""You are a professional threat intelligence analyst. Your task is to create a collection plan and suggest relevant sources for the given Priority Intelligence Requirements (PIRs).

## Priority Intelligence Requirements
{pir}
{modifications_section}
## Available Sources
The following sources are available: {available_sources_str}
Only suggest sources that are genuinely relevant to the PIRs.

## Allowed Tools
You MUST only use list_knowledge_base and read_knowledge_base.
Do not call any other tools during planning.

## Instructions
1. Read the knowledge bank (use list_knowledge_base and read_knowledge_base) to understand available background knowledge
2. Based on the PIRs and background knowledge, write one step per PIR — each step explains what to collect for that specific requirement, from which source, and why
3. Select which sources are most relevant to answer the PIRs

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown.
You MUST include all three fields: "plan", "steps", and "suggested_sources".

{{
  "plan": "Full collection plan as a single text string (used internally)",
  "steps": [
    {{
      "title": "Short title describing this PIR's collection goal (max 8 words)",
      "description": "Detailed explanation of what to collect, from which source, and why"
    }}
  ],
  "suggested_sources": ["source name as listed in Available Sources"]
}}

{lang_note}"""

def build_collection_collect_prompt(
    pir: str,
    selected_sources: list,
    plan: str,
    session_id: str | None = None,
    since_date: str | None = None,
    existing_data: str | None = None,
    perspectives: list[str] | None = None,
) -> str:
    approved_tools = [
        tool
        for s in selected_sources if s in SOURCE_TOOL_MAP
        for tool in SOURCE_TOOL_MAP[s]
    ]
    unmapped = [s for s in selected_sources if s not in SOURCE_TOOL_MAP]

    approved_tools_str = ", ".join(approved_tools) if approved_tools else "none"
    unmapped_note = (
        f"\nNote: The following selected sources could not be mapped to tools "
        f"and will be skipped: {', '.join(unmapped)}"
        if unmapped else ""
    )
    _upload_tools_in_use = [t for t in ["list_uploads", "search_local_data", "read_upload"] if t in approved_tools]
    session_note = (
        f"\nNote: For uploaded document tools, always use session_id=\"{session_id}\". "
        f"Workflow: (1) call list_uploads(session_id) to see available files and their file_ids; "
        f"(2) call search_local_data(session_id, query) for keyword-relevant snippets; "
        f"(3) call read_upload(session_id, file_upload_id) to read the full content of relevant files."
        if session_id and _upload_tools_in_use else ""
    )
    _min_lookback = (datetime.now(UTC).replace(year=datetime.now(UTC).year - 3)).strftime('%Y-%m-%d')
    since_note = (
        f"\nNote: Today's date is {datetime.now(UTC).strftime('%Y-%m-%d')}. The PIR timeframe is \"{since_date}\". "
        f"For all query_otx calls, use since_date=\"{_min_lookback}\" (3 years ago) to ensure sufficient historical coverage."
        if since_date and "query_otx" in approved_tools else ""
    )

    existing_data_section = (
        f"\n## Already Collected Data\nThe following data was gathered in a previous attempt. "
        f"Do NOT re-collect data that is already here. Only collect NEW data not yet covered.\n{existing_data}"
        if existing_data else ""
    )

    _PERSP_REGION_LANG: dict[str, tuple[str, str]] = {
        "us":      ("us",   "en"),
        "eu":      ("gb",   "en"),
        "norway":  ("no",   "no"),
        "china":   ("cn",   "zh-cn"),
        "russia":  ("ru",   "ru"),
        "neutral": ("",     ""),
    }
    _active = [p for p in (perspectives or []) if p != "neutral"]
    if not _active:
        _active = ["neutral"]
    _has_web_tools = "google_search" in approved_tools or "google_news_search" in approved_tools
    if _has_web_tools:
        _persp_str = ", ".join(perspectives) if perspectives else "neutral"
        _timelimit_hint = since_date or "unspecified"
        _mapping_lines = "\n".join(
            f"  {p:<8} → region=\"{_PERSP_REGION_LANG.get(p, ('',''))[0] or 'omit'}\", language=\"{_PERSP_REGION_LANG.get(p, ('',''))[1] or 'omit'}\""
            for p in _active
        )
        _web_examples = "\n".join(
            (
                f"  google_search(query=\"<topic> {p} perspective\", num_results=5, "
                f"region=\"{_PERSP_REGION_LANG.get(p, ('',''))[0]}\", "
                f"language=\"{_PERSP_REGION_LANG.get(p, ('',''))[1]}\", date_restrict=\"<code>\")"
            )
            for p in _active
        )
        _news_examples = "\n".join(
            (
                f"  google_news_search(query=\"<topic> {p} latest\", num_results=5, "
                f"region=\"{_PERSP_REGION_LANG.get(p, ('',''))[0]}\", "
                f"language=\"{_PERSP_REGION_LANG.get(p, ('',''))[1]}\", date_restrict=\"<code>\")"
            )
            for p in _active
        )
        _max_web = len(_active) * 5
        _max_news = len(_active) * 5
        web_search_note = (
            f"\n## Web Search Guidance"
            f"\nPerspectives selected: {_persp_str}"
            f"\nPerspective → region + language mapping:"
            f"\n{_mapping_lines}"
            f"\nAlways pass region and language when calling either tool."
            f"\n"
            f"\nFor EACH perspective call BOTH tools separately:"
            f"\n  1. google_search  — background reports, analysis, deep web"
            f"\n  2. google_news_search — recent/breaking news, press releases"
            f"\n"
            f"\nInclude the perspective in every query string:"
            f"\n  BAD:  google_search(query=\"GPS jamming\")"
            f"\n  GOOD: google_search(query=\"GPS jamming Russia perspective\", region=\"ru\", language=\"ru\")"
            f"\n"
            f"\ngoogle_search examples:"
            f"\n{_web_examples}"
            f"\n"
            f"\ngoogle_news_search examples:"
            f"\n{_news_examples}"
            f"\n"
            f"\nTimeframe hint: \"{_timelimit_hint}\""
            f"\ndate_restrict codes: \"d1\"=day, \"w1\"=week, \"m1\"=month, \"m3\"=3 months, \"m6\"=6 months, \"y1\"=year. Omit for no restriction."
            f"\nSTRICT LIMITS: max {_max_web} google_search calls + max {_max_news} google_news_search calls ({len(_active)} perspective(s) × 5 each)."
            f"\nSource authority: web search results carry LOWER authority than OTX. Always prefer OTX."
        )
    else:
        web_search_note = ""

    return f"""You are a threat intelligence data collector. Your only task is to retrieve raw data from approved sources. Do not summarize, interpret, or draw conclusions.

## Approved PIRs
{pir}

## Collection Plan
{plan}
{existing_data_section}
## Approved Tools
You MUST only use the following tools: {approved_tools_str}
Do not query any source or tool not listed above.{unmapped_note}{session_note}{since_note}
{web_search_note}

## Instructions
1. Use the approved tools to collect data relevant to the PIRs only
2. For query_otx: only search for threat actors, APT groups, and country names that are explicitly mentioned in the PIRs above (e.g. "APT29", "Russia", "GRU"). Do NOT search for generic terms like "energy sector", "reconnaissance", "network mapping", or "vulnerability identification". One search term per call. query_otx automatically returns full details (IoCs, TTPs, description, targeted countries) for the top results — no follow-up calls needed.
3. For knowledge base tools: read each relevant resource separately
4. Return content verbatim — do not summarize, rephrase, or interpret
5. If a source returns no relevant data, still include it in output with empty content

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown.

IMPORTANT: The "content" field must be a plain text string — never a JSON object or nested structure.
Copy only the text string the tool returned. Do not wrap it in {{"result": ...}} or any other object.

{{
  "collected_data": [
    {{
      "source": "tool_name",
      "resource_id": "resource identifier if applicable, else null",
      "content": "plain text string returned by the tool — no JSON wrapping"
    }}
  ]
}}"""


def build_processing_prompt(
    pir: str,
    collected_data: str,
    feedback: str | None = None,
) -> str:
    feedback_section = (
        f"\n## Reviewer Feedback\nThe previous attempt was rejected. Apply this feedback:\n{feedback}\n"
        if feedback else ""
    )

    return f"""You are a professional threat intelligence analyst. Your task is to process raw collected intelligence data into structured PMESII entities ready for analysis.

## Priority Intelligence Requirements
{pir}

## Collected Raw Data
{collected_data}
{feedback_section}
## Your Task
Work through four steps:

**Step 1 — Normalize**
Extract all meaningful entities from the collected data:
- Cyber IoCs: IP addresses, domains, hashes, CVEs
- Threat actors: APT groups, state-sponsored groups, criminal organizations
- Countries, regions, military units
- Organizations (government, military, corporate, NGO)
- Events and incidents
- Infrastructure (physical or digital)

**Step 2 — Enrich**
For each extracted entity, use available tools to gather additional context:
- For IoCs: call lookup_indicator_otx(indicator_type, value)
- For threat actors, countries, organizations: call list_knowledge_base() then read_knowledge_base(resource_id)
- For recent events: call google_search or google_news_search
Limit IoC lookups to 12 maximum.

**Step 3 — Correlate**
Identify patterns across enriched entities:
- Same entity confirmed by multiple sources → higher confidence
- Multiple IoCs linked to same actor or campaign
- Entities active within the PIR timeframe
- State or group attribution chains

**Step 4 — Synthesize**
Convert findings into PMESIIEntity objects. One entity per meaningful observation.
Keep descriptions narrow and factual. Use tags broadly for relations and context.

## PMESII Categories
Assign one or more categories per entity:
- political: governance, diplomacy, policy, elections
- military: armed forces, weapons, operations, doctrine
- economic: trade, sanctions, energy, finance
- social: population, culture, ideology, public opinion
- information: media, cyber, propaganda, signals
- infrastructure: physical systems, networks, utilities, transport

## Valid Source Values
otx, knowledge_base, web_search, csv_upload, pdf_upload, txt_upload, json_upload

## Confidence Scoring
- 40-55: Single source, unverified
- 60-70: Single reliable source (OTX or KB) with reasonable support
- 70-80: Confirmed by OTX with multiple pulses, or two independent sources
- 80-90: Confirmed by multiple independent sources
- 90+: Three or more sources with consistent attribution

## Processing Summary Format
Write one line per PIR with status and key entities found:
PIR-1 (short description): Answered
  → EntityA, EntityB (high confidence). N entities.
PIR-2 (short description): Gap
  → No data found after 2023.
PIR-3 (short description): Partially answered
  → EntityC (low confidence). Key gap: X unknown.

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown.

{{
  "entities": [
    {{
      "id": "e1",
      "name": "Short entity name",
      "description": "Factual description — no interpretation or conclusions",
      "categories": ["military"],
      "sources": ["otx"],
      "confidence": 75,
      "relevant_to": ["PIR-1"],
      "tags": ["russia", "apt29", "energy-sector"],
      "first_observed": "2024-01-01",
      "last_updated": "2024-03-15"
    }}
  ],
  "gaps": [
    "PIR-2: No data found on Iranian naval movements after 2023"
  ],
  "processing_summary": "PIR-1: Answered\\n  → ...",
  "assessment_changed": false,
  "change_summary": null
}}"""


def build_processing_modify_prompt(
    existing_result: str,
    modifications: str,
) -> str:
    return f"""You are a professional threat intelligence analyst. Apply the requested modification to an existing processing result.

## Modification Request
{modifications}

## Existing Processing Result
{existing_result}

## Instructions
1. Apply only the requested changes — do not re-run tool calls or re-process data
2. Preserve all entities and findings not mentioned in the modification request
3. Keep the same JSON structure

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown.
Same structure as the input."""


def build_collection_summarize_prompt(
    pir: str,
    collected_data: str,
    language: str = "en"
) -> str:
    lang_note = _language_instruction(language)

    return f"""You are a professional threat intelligence analyst. Your task is to produce a factual summary of collected intelligence data. You have no tools — work only from the data provided.

## Approved PIRs
{pir}

## Collected Data
{collected_data}

## Instructions
1. Summarize what was found and which source it came from — factual, no interpretation, no conclusions
2. Explicitly link findings to the relevant PIRs
3. Report gaps: what was required by the PIRs but not found in the collected data

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown.

{{
  "summary": "Factual narrative of what was found, from which sources, and which PIRs it is relevant to",
  "sources_used": ["source1", "source2"],
  "gaps": "What was required by the PIRs but not found — or null if no gaps"
}}

{lang_note}"""
