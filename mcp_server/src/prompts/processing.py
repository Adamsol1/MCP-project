"""Processing phase prompt builders and MCP adapter functions."""


def build_processing_prompt(
    pir: str,
    collected_data: str,
    feedback: str | None = None,
) -> str:
    feedback_section = (
        f"\n## Analyst Feedback from Previous Attempt\n{feedback}\nAddress this feedback in your processing."
        if feedback else ""
    )

    return f"""You are a professional threat intelligence analyst in the Processing phase of the intelligence cycle. Your task is to transform raw collected intelligence data into structured, analytical findings.

## Priority Intelligence Requirements
{pir}

## Collected Intelligence Data
{collected_data}
{feedback_section}

## Instructions
1. Analyse the collected data against the PIRs
2. Produce discrete findings — each finding should capture one analytical point
3. For each finding, identify:
   - A short descriptive title
   - A detailed analytical narrative (the "finding" field)
   - A concise evidence summary
   - The source category (e.g. "osint", "knowledge_bank", "network_telemetry", "malware_analysis", "web_search")
   - A confidence score from 0 to 100 based on source reliability and corroboration
   - Which PIRs it addresses
   - Supporting data: IOCs, MITRE ATT&CK IDs, entities, domains, timestamps, locations, KB references — as applicable
   - Why it matters analytically
   - Any uncertainties or limitations
4. Respect the timeframe specified in the PIRs. Only include timestamps in supporting_data that fall within (or are directly relevant to) that timeframe. Historical events may be referenced in the finding narrative for context, but supporting_data.timestamps should reflect the analytical window, not distant historical dates.
5. Use the knowledge base tools to enrich your analysis with background context
6. Use web search tools to verify or supplement findings where needed
7. Identify analytical gaps — what the PIRs require but the data does not support

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown fences.

{{
  "findings": [
    {{
      "id": "F-001",
      "title": "Short finding title",
      "finding": "Detailed analytical narrative of the finding",
      "evidence_summary": "Concise summary of the supporting evidence",
      "source": "source_category",
      "confidence": 75,
      "relevant_to": ["PIR-0", "PIR-1"],
      "supporting_data": {{
        "iocs": ["indicator1", "indicator2"],
        "attack_ids": ["T1078", "T1110.003"],
        "entities": ["Organization", "System"],
        "domains": ["example.com"],
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
