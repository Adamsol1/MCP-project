"""Processing phase prompt builders and MCP adapter functions."""


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


# ── MCP adapter functions ─────────────────────────────────────────────────────


def processing_process(
    pir: str,
    collected_data: str,
    feedback: str = "",
) -> str:
    """Prompt for processing raw collected data into structured PMESII entities.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        collected_data: Raw data JSON returned by the collection agent.
        feedback: Optional reviewer feedback from a previous rejected attempt.
    """
    return build_processing_prompt(
        pir=pir,
        collected_data=collected_data,
        feedback=feedback or None,
    )


def processing_modify(
    existing_result: str,
    modifications: str,
) -> str:
    """Prompt for applying analyst modifications to an existing processing result.

    Args:
        existing_result: The existing processing result (JSON string).
        modifications: The analyst's requested changes.
    """
    return build_processing_modify_prompt(
        existing_result=existing_result,
        modifications=modifications,
    )
