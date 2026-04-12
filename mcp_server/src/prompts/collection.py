"""Collection phase prompt builders and MCP adapter functions."""

import json
from datetime import UTC, datetime

from ._shared import SOURCE_TOOL_MAP, _language_instruction


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
2. Based on the PIRs and background knowledge, write a concise step-by-step collection plan
3. Select which sources are most relevant to answer the PIRs

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown.

{{
  "plan": "Step-by-step collection plan describing what to collect, from which sources, and why",
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
        f"Do NOT duplicate content already present here, but you MUST still query ALL approved sources — "
        f"each source may have additional data not yet covered. "
        f"Use different queries, angles, or resources to fill the gaps identified by the reviewer.\n{existing_data}"
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
        _timelimit_hint = since_date or "unspecified"
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
            f"\nTimeframe hint: \"{_timelimit_hint}\""
            f"\ndate_restrict codes: \"d1\"=day, \"w1\"=week, \"m1\"=month, \"m3\"=3 months, \"m6\"=6 months, \"y1\"=year. Omit for no restriction."
            f"\nSTRICT LIMITS: max {_max_web} google_search calls ({len(_active)} perspective(s) × 5 each)."
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


# ── MCP adapter functions ─────────────────────────────────────────────────────


def collection_plan(
    pir: str,
    modifications: str = "",
    language: str = "en",
) -> str:
    """Prompt for generating a collection plan and suggesting relevant sources.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        modifications: Optional user feedback to modify an existing plan.
        language: BCP-47 language code (e.g. "en", "no").
    """
    return build_collection_plan_prompt(
        pir=pir,
        modifications=modifications or None,
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
    """
    return build_collection_collect_prompt(
        pir=pir,
        selected_sources=json.loads(selected_sources),
        plan=plan,
        session_id=session_id or None,
        since_date=since_date or None,
        existing_data=existing_data or None,
        perspectives=json.loads(perspectives) or None,
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
