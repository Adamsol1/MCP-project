"""Processing phase prompt builders and MCP adapter functions."""

from datetime import UTC, datetime

from ._shared import _language_instruction


def build_processing_prompt(
    pir: str,
    collected_data: str,
    feedback: str | None = None,
    previous_result: str | None = None,
    language: str = "en",
) -> str:
    _today = datetime.now(UTC).strftime('%Y-%m-%d')
    lang_note = _language_instruction(language, "all output fields")

    feedback_section = (
        f"\n## Analyst Feedback from Previous Attempt\n{feedback}\nAddress this feedback in your processing."
        if feedback else ""
    )
    previous_section = (
        f"\n## Previous Processing Result\nThis is the analysis from the previous collection run.\n"
        f"Compare your new findings against it. Set `assessment_changed: true` and write a `change_summary`\n"
        f"if your conclusions about the PIRs differ materially (new threats identified, confidence shifts,\n"
        f"gaps filled, or prior findings contradicted). Set `assessment_changed: false` if the new data\n"
        f"only adds minor detail without changing the overall picture.\n\n{previous_result}\n"
        if previous_result else ""
    )

    return f"""{lang_note}You are a professional threat intelligence analyst. Your task is to process raw collected intelligence data into structured PMESII entities ready for analysis.

TODAY'S DATE: {_today}
Use this as the reference point for all temporal reasoning, including PIR timeframes and recency assessments.

## Priority Intelligence Requirements
{pir}

## Collected Intelligence Data
{collected_data}
{previous_section}{feedback_section}

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
Assign exactly ONE primary category per finding:
- political: governance, diplomacy, policy, elections
- military: armed forces, weapons, operations, doctrine
- economic: trade, sanctions, energy, finance
- social: population, culture, ideology, public opinion
- information: media, cyber, propaganda, signals
- infrastructure: physical systems, networks, utilities, transport

Choose the single most relevant category. Do not assign multiple categories.
**If you are genuinely uncertain between exactly two categories**, call `request_pmesii_clarification` with the finding title, the two candidate categories, and one sentence explaining why both could apply.
Use the analyst's answer as the sole category for that finding.

## Valid Source Values
otx, knowledge_base, web_search, csv_upload, pdf_upload, txt_upload, json_upload

## Confidence Scoring
- 40-55: Single source, unverified
- 60-69: Single reliable source (OTX or KB) with reasonable support
- 70-79: Confirmed by OTX with multiple pulses, or two independent sources
- 80-89: Confirmed by multiple independent sources
- 90+: Three or more sources with consistent attribution

## PIR Numbering
PIRs are numbered starting from 1. The first PIR in the list is PIR-1, the second is PIR-2, etc.
Use this 1-based numbering consistently in all `relevant_to` fields and in the Processing Summary.

## Processing Summary Format
Write one line per PIR with status and key entities found:
PIR-1 (short description): Answered
  → EntityA, EntityB (high confidence). N entities.
PIR-2 (short description): Gap
  → No data found after 2023.
PIR-3 (short description): Partially answered
  → EntityC (low confidence). Key gap: X unknown.

## Source Attribution
For every finding, record the specific collected items that directly support it:
- Web articles (fetch_page / google_search / google_news_search): add full URLs to `supporting_data.source_urls`
- Knowledge base entries: add the resource_id values to `supporting_data.kb_refs`
- Uploaded files (pdf_upload / csv_upload / txt_upload / json_upload): add the resource_id (filename) to `supporting_data.source_refs`
- OTX / IoC lookups: add the indicator values to `supporting_data.iocs`
Always populate whichever fields are relevant. Multiple source types may be present in the same finding.

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown fences.

{{
  "findings": [
    {{
      "id": "F-01",
      "title": "2-4 word entity name (e.g. 'APT41', 'Iran Power Grid', 'PLA Cyber Command')",
      "finding": "Detailed analytical narrative of the finding",
      "evidence_summary": "Concise summary of the supporting evidence",
      "source": "web_search",
      "confidence": 75,
      "categories": ["military"],
      "relevant_to": ["PIR-1", "PIR-2"],
      "supporting_data": {{
        "iocs": ["indicator1", "indicator2"],
        "attack_ids": ["T1078", "T1110.003"],
        "entities": ["Organization", "System"],
        "domains": ["example.com"],
        "source_urls": ["https://example.com/article-slug"],
        "source_refs": ["uploaded_report.pdf"],
        "timestamps": ["2026-01-15T00:00:00Z"],
        "locations": ["Oslo, Norway"],
        "kb_refs": ["knowledge_base_reference"]
      }},
      "why_it_matters": "Analytical significance of this finding",
      "uncertainties": ["Known limitation or gap"]
    }}
  ],
  "gaps": ["What the PIRs require but could not be determined from the data"]
}}"""


def build_processing_modify_prompt(
    existing_result: str,
    modifications: str,
    language: str = "en",
) -> str:
    lang_note = _language_instruction(language, "the modified output")

    return f"""{lang_note}You are a professional threat intelligence analyst. Apply the requested modification to an existing processing result.

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
    previous_result: str = "",
    language: str = "en",
) -> str:
    """Prompt for processing raw collected data into structured PMESII entities.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        collected_data: Raw data JSON returned by the collection agent.
        feedback: Optional reviewer feedback from a previous rejected attempt.
        previous_result: Optional JSON string of the previous processing result.
                         When provided, the LLM compares findings and sets assessment_changed.
    """
    return build_processing_prompt(
        pir=pir,
        collected_data=collected_data,
        feedback=feedback or None,
        previous_result=previous_result or None,
        language=language,
    )


def processing_modify(
    existing_result: str,
    modifications: str,
    language: str = "en",
) -> str:
    """Prompt for applying analyst modifications to an existing processing result.

    Args:
        existing_result: The existing processing result (JSON string).
        modifications: The analyst's requested changes.
    """
    return build_processing_modify_prompt(
        existing_result=existing_result,
        modifications=modifications,
        language=language,
    )
