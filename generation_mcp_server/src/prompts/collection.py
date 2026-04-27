"""Collection phase prompt builders and MCP adapter functions."""

import json
from datetime import UTC, datetime, timedelta

from ._shared import SOURCE_TOOL_MAP, _language_instruction


def _code_to_date(code: str) -> str:
    """Convert a timeframe code (e.g. 'y3', 'm3') to a YYYY-MM-DD cutoff date.
    Falls back to 3 years ago for empty or unrecognised codes.
    """
    now = datetime.now(UTC)
    fallback_year = now.year - 3
    try:
        fallback = now.replace(year=fallback_year).strftime("%Y-%m-%d")
    except ValueError:
        fallback = now.replace(year=fallback_year, day=28).strftime("%Y-%m-%d")
    if not code:
        return fallback
    unit = code[0]  # d / w / m / y
    try:
        n = int(code[1:])
    except (ValueError, IndexError):
        return fallback
    try:
        if unit == "d":
            dt = now - timedelta(days=n)
        elif unit == "w":
            dt = now - timedelta(weeks=n)
        elif unit == "m":
            dt = now - timedelta(days=n * 30)
        elif unit == "y":
            try:
                dt = now.replace(year=now.year - n)
            except ValueError:
                dt = now.replace(year=now.year - n, day=28)
        else:
            return fallback
    except Exception:
        return fallback
    return dt.strftime("%Y-%m-%d")


def build_collection_plan_prompt(
    pir: str,
    modifications: str | None = None,
    current_plan: str | None = None,
    language: str = "en",
) -> str:
    available_sources = list(SOURCE_TOOL_MAP.keys())
    available_sources_str = ", ".join(f'"{s}"' for s in available_sources)
    lang_note = _language_instruction(language, "the 'plan' field")

    existing_plan_section = (
        f"\n## Existing Plan\n{current_plan}\n"
        if current_plan else ""
    )

    modifications_section = (
        f"\n## Modification Request\n{modifications}\n"
        f"Use the following rules to decide how to respond:\n"
        f"- Additive (e.g. 'add a step for X', 'include a step on Y'):\n"
        f"  Keep ALL existing steps unchanged and append only the new step(s). Do not modify, merge, or remove any existing steps.\n"
        f"- Specific (e.g. 'change step 2', 'step 3 is too vague'):\n"
        f"  Keep all other steps unchanged and only modify the ones explicitly mentioned.\n"
        f"- General (e.g. 'too broad', 'not relevant'):\n"
        f"  Regenerate all steps from scratch using the feedback as guidance.\n"
        if modifications else ""
    )

    return f"""{lang_note}You are a professional threat intelligence analyst. Your task is to create a collection plan and suggest relevant sources for the given Priority Intelligence Requirements (PIRs).

## Priority Intelligence Requirements
{pir}
{existing_plan_section}{modifications_section}
## Available Sources
The following sources are available: {available_sources_str}
Only suggest sources that are genuinely relevant to the PIRs.

## Allowed Tools
During planning, call ONLY list_knowledge_base and read_knowledge_base.
Any other tool calls are not permitted at this stage.

## Instructions
1. Read the knowledge bank (use list_knowledge_base and read_knowledge_base) to understand available background knowledge
2. Break the collection task into discrete steps — one step per PIR or coherent intelligence theme
3. For each step, select only the sources from Available Sources that are genuinely useful for that specific step

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown.

{{
  "steps": [
    {{
      "title": "Short step title (e.g. PIR-0 title or theme)",
      "description": "What to collect for this step, why it matters, and what angle to take",
      "suggested_sources": ["source name as listed in Available Sources"]
    }}
  ]
}}

Each step must have at least one suggested_source. Only use source names exactly as listed in Available Sources."""


def build_collection_collect_prompt(
    pir: str,
    selected_sources: list,
    plan: str,
    session_id: str | None = None,
    since_date: str | None = None,
    existing_data: str | None = None,
    perspectives: list[str] | None = None,
    step_source_guidance: str | None = None,
    source_timeframes: dict[str, str] | None = None,
    language: str = "en",  # noqa: ARG001 - raw source content must remain verbatim.
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
    _now = datetime.now(UTC)
    _stf = source_timeframes or {}
    _otx_lookback = _code_to_date(_stf.get("otx", ""))
    since_note = (
        f"\nNote: Today's date is {_now.strftime('%Y-%m-%d')}. The PIR timeframe is \"{since_date}\". "
        f"For all query_otx calls, use since_date=\"{_otx_lookback}\"."
        if "query_otx" in approved_tools else ""
    )

    existing_data_section = (
        f"\n## Already Collected Data\nThe following data was gathered in a previous attempt. "
        f"Do NOT reproduce identical content already present here. "
        f"A source is NOT considered covered if only partial data was collected — "
        f"query it again with different search terms or angles to fill remaining gaps. "
        f"You MUST still query ALL approved sources.\n{existing_data}"
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
    _has_web_tools = "google_search" in approved_tools
    if _has_web_tools:
        _persp_str = ", ".join(perspectives) if perspectives else "neutral"
        _mapping_lines = "\n".join(
            f"  {p:<8} → region=\"{_PERSP_REGION_LANG.get(p, ('',''))[0] or 'omit'}\", language=\"{_PERSP_REGION_LANG.get(p, ('',''))[1] or 'omit'}\""
            for p in _active
        )
        _web_examples = "\n".join(
            (
                f"  google_search(query=\"<topic> {p} perspective\", num_results=10, "
                f"region=\"{_PERSP_REGION_LANG.get(p, ('',''))[0]}\", "
                f"language=\"{_PERSP_REGION_LANG.get(p, ('',''))[1]}\", date_restrict=\"<code>\")"
            )
            for p in _active
        )
        _max_web = len(_active) * 5
        web_search_note = (
            f"\n## Web Search Guidance"
            f"\nPerspectives selected: {_persp_str}"
            f"\nPerspective → region + language mapping:"
            f"\n{_mapping_lines}"
            f"\nAlways pass region and language when calling google_search."
            f"\n"
            f"\nIMPORTANT: google_search is used for URL discovery only. The backend will fetch and"
            f"\nsummarise the full content of each page — your snippets are not stored as intelligence."
            f"\n"
            f"\n## Query Construction Rules"
            f"\nWrite narrow, specific queries — not broad topic keywords."
            f"\nBad queries match too many unrelated pages (military hardware wikis, hobby sites, blogs)."
            f"\nGood queries combine: a specific named entity or event + the analytic angle + the source type."
            f"\n"
            f"\nQuery construction:"
            f"\n  BAD:  \"China military Taiwan\"                → too broad, matches everything"
            f"\n  BAD:  \"GPS jamming\"                         → matches hobby and history pages"
            f"\n  GOOD: \"Volt Typhoon critical infrastructure pre-positioning CISA analysis\""
            f"\n  GOOD: \"PLA amphibious capability assessment 2025 RAND\""
            f"\n  GOOD: \"Russia hybrid warfare Norway Nordic analysis site:nato.int OR site:rand.org\""
            f"\n"
            f"\nTips for precision:"
            f"\n  - Use named threat actors, operations, or policy names (e.g. 'Volt Typhoon', 'Operation X')"
            f"\n  - Add source-type words: 'analysis', 'assessment', 'report', 'white paper'"
            f"\n  - Add known authoritative domains with OR: 'site:csis.org OR site:rand.org OR site:rusi.org'"
            f"\n  - Use year or date range when timeframe matters: '2025' or '2024 2025'"
            f"\n"
            f"\nSource authority hierarchy — prefer queries that surface sources in this order:"
            f"\n  1. Government & official sources (.gov, .mil, ministry/agency sites)"
            f"\n  2. Established research institutions & think tanks (CSIS, RAND, Chatham House, RUSI, CFR, Brookings, ISW)"
            f"\n  3. Trusted international news outlets (Reuters, BBC, AP, Financial Times, etc.)"
            f"\n  4. Other credible sources"
            f"\n"
            f"\nUse num_results=10 per call."
            f"\n"
            f"\ngoogle_search examples:"
            f"\n{_web_examples}"
            f"\n"
            f"\n## Per-Source-Type Timeframes"
            f"\nApply these date_restrict codes based on the type of source the query targets:"
            f"\n  Government & official (.gov, .mil, ministry/agency, state media): date_restrict=\"{_stf.get('web_gov', '') or 'omit'}\""
            f"\n  Think tanks & research (RAND, CSIS, Chatham House, RUSI, CFR):    date_restrict=\"{_stf.get('web_think_tank', '') or 'omit'}\""
            f"\n  News & media (Reuters, BBC, AP, FT, national newspapers):          date_restrict=\"{_stf.get('web_news', '') or 'omit'}\""
            f"\n  Other web sources:                                                  date_restrict=\"{_stf.get('web_other', '') or 'omit'}\""
            f"\nIf the code is 'omit', do not pass date_restrict for that query."
            f"\nWhen a query mixes types (no site: restriction), use the tier most likely to satisfy the PIR."
            f"\ndate_restrict codes: d1=day, w1=week, m1=month, m3=3 months, m6=6 months, y1=year, y2=2 years, y3=3 years."
            f"\nSTRICT LIMITS: max {_max_web} google_search calls ({len(_active)} perspective(s) × 5 each)."
            f"\nSource authority: web search results carry LOWER authority than OTX. Always prefer OTX."
        )
    else:
        web_search_note = ""

    step_guidance_section = f"\n{step_source_guidance}\n" if step_source_guidance else ""

    return f"""You are a threat intelligence data collector. Your only task is to retrieve raw data from approved sources. Do not summarize, interpret, or draw conclusions.

## Approved PIRs
{pir}

## Collection Plan
{plan}
{step_guidance_section}{existing_data_section}
## Approved Tools
You MUST only use the following tools: {approved_tools_str}
Do not query any source or tool not listed above.
If you are unsure whether a tool is approved, do not call it — unauthorised tool calls will be rejected.{unmapped_note}{session_note}{since_note}
{web_search_note}

## Instructions
1. Use ALL approved tools — do not skip any source that was approved by the user
2. For query_otx: only search for threat actors, APT groups, and country names that are explicitly mentioned in the PIRs above (e.g. "APT29", "Russia", "GRU"). Do NOT search for generic terms like "energy sector", "reconnaissance", "network mapping", or "vulnerability identification". One search term per call. query_otx automatically returns full details (IoCs, TTPs, description, targeted countries) for the top results — no follow-up calls needed.
3. For knowledge base tools: read each relevant resource separately
4. For uploaded document tools: you MUST call list_uploads first to see what files are available, then read any that may be relevant to the PIRs. Do not skip uploads without checking.
5. Return content verbatim — do not summarize, rephrase, or interpret
6. If a source returns no relevant data, still include it in output with empty content

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown.

IMPORTANT: The "content" field must be a plain text string — never a JSON object or nested structure.
Copy only the text string the tool returned. Do not wrap it in {{"result": ...}} or any other object.

CRITICAL for google_search: Output ONE separate item per result URL.
Do NOT bundle all results from one search call into a single item.
Set "resource_id" to the URL of that specific result. Set "content" to its title and snippet text.
Example — a search returning 3 URLs becomes 3 separate items:
{{
  "collected_data": [
    {{
      "source": "google_search",
      "resource_id": "https://example.gov/report",
      "content": "Title: Report Title\nSnippet: The snippet text for this specific result."
    }},
    {{
      "source": "google_search",
      "resource_id": "https://think-tank.org/analysis",
      "content": "Title: Analysis Title\nSnippet: The snippet text for this specific result."
    }}
  ]
}}

For all other tools (knowledge base, OTX, uploads), one item per tool call is fine:
{{
  "collected_data": [
    {{
      "source": "tool_name",
      "resource_id": "resource identifier if applicable, else null",
      "content": "plain text string returned by the tool — no JSON wrapping"
    }}
  ]
}}"""


def build_collection_summarize_prompt(
    pir: str,
    collected_data: str,
    language: str = "en",
) -> str:
    lang_note = _language_instruction(language)

    return f"""{lang_note}You are a professional threat intelligence analyst. Your task is to produce a factual summary of collected intelligence data. You have no tools — work only from the data provided.

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
  "gaps": "What was required by the PIRs but not found — use JSON null (not the string 'null') if no gaps were identified"
}}"""


def build_collection_modify_prompt(
    collected_data: str,
    modifications: str,
    language: str = "en",
) -> str:
    lang_note = _language_instruction(language, "the 'summary' and 'gaps' fields")

    return f"""{lang_note}You are a professional threat intelligence analyst. Apply the requested modification to an existing intelligence summary.

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
  "gaps": "Updated gaps — use JSON null (not the string 'null') if no gaps were identified"
}}"""


# ── MCP adapter functions ─────────────────────────────────────────────────────


def collection_plan(
    pir: str,
    modifications: str = "",
    current_plan: str = "",
    language: str = "en",
) -> str:
    """Prompt for generating a collection plan and suggesting relevant sources.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        modifications: Optional user feedback to modify an existing plan.
        current_plan: The existing plan to modify (JSON string).
        language: BCP-47 language code (e.g. "en", "no").
    """
    return build_collection_plan_prompt(
        pir=pir,
        modifications=modifications or None,
        current_plan=current_plan or None,
        language=language,
    )


def collection_collect(
    pir: str,
    selected_sources: str,
    plan: str,
    session_id: str = "",
    since_date: str = "",
    existing_data: str = "",
    perspectives: str = "[]",
    step_source_guidance: str = "",
    source_timeframes: str = "{}",
    language: str = "en",
) -> str:
    """Prompt for collecting raw intelligence data via tools in the Collection phase.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        selected_sources: JSON array of source names approved by the analyst.
        plan: The approved collection plan text.
        session_id: Session ID used for search_local_data (uploaded documents).
        since_date: ISO date (YYYY-MM-DD) to filter OTX pulses by modification date.
        existing_data: Raw data already collected in previous attempts (for retry context).
        perspectives: JSON array of geopolitical perspectives from the Direction phase.
        step_source_guidance: Per-step source availability guidance for the agent.
        source_timeframes: JSON object mapping source-tier keys to date_restrict codes.
    """
    return build_collection_collect_prompt(
        pir=pir,
        selected_sources=json.loads(selected_sources),
        plan=plan,
        session_id=session_id or None,
        since_date=since_date or None,
        existing_data=existing_data or None,
        perspectives=json.loads(perspectives) or None,
        step_source_guidance=step_source_guidance or None,
        source_timeframes=json.loads(source_timeframes) or None,
        language=language,
    )


def collection_summarize(
    pir: str,
    collected_data: str,
    language: str = "en",
) -> str:
    """Prompt for summarizing raw collected data in the Collection phase.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        collected_data: Raw data JSON returned by the collection agent.
        language: BCP-47 language code (e.g. "en", "no").
    """
    return build_collection_summarize_prompt(
        pir=pir,
        collected_data=collected_data,
        language=language,
    )


def collection_modify(
    collected_data: str,
    modifications: str,
    language: str = "en",
) -> str:
    """Prompt for applying analyst modifications to an existing collection summary.

    Args:
        collected_data: The existing collected summary (JSON string).
        modifications: The analyst's requested changes.
        language: BCP-47 language code (e.g. "en", "no").
    """
    return build_collection_modify_prompt(
        collected_data=collected_data,
        modifications=modifications,
        language=language,
    )
