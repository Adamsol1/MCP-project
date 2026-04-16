"""Analysis phase prompt builders and MCP adapter functions.

AI #1 (generator) prompt for synthesising processed findings into an AnalysisDraft.
The corresponding AI #2 (reviewer) prompt lives in review_mcp_server/src/prompts/analysis.py.
"""


def build_analysis_generate_prompt(
    pir: str,
    findings: str,
) -> str:
    return f"""You are drafting an intelligence-analysis summary for an analyst UI.

Use the processed findings below as the primary evidence base.
Do NOT search for additional data, call any tools, or introduce information not present in the findings.
Your role is synthesis and interpretation — not collection.

## Priority Intelligence Requirements
{pir}

## Processed Findings (JSON)
{findings}

## Requirements
- Be analytical, specific, and grounded in the findings.
- Do not mention being an AI.
- Summary must be 2–4 sentences.
- Key judgments must be distinct and substantive — do not restate findings verbatim.
- For each perspective, provide 2 concise implications as objects with "assertion" and "supporting_finding_ids".
- supporting_finding_ids must only contain finding IDs present in the findings above (e.g. "F-001").
- If an implication cannot be traced to a specific finding, use an empty array [].
- Recommended actions must be actionable and analyst-relevant.
- information_gaps must reflect the gaps listed in the findings — do not invent new ones.

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown fences.

{{
  "summary": "string",
  "key_judgments": ["string"],
  "per_perspective_implications": {{
    "us": [
      {{
        "assertion": "string — analytical implication",
        "supporting_finding_ids": ["F-001"]
      }}
    ],
    "norway": [{{"assertion": "string", "supporting_finding_ids": []}}],
    "china": [{{"assertion": "string", "supporting_finding_ids": []}}],
    "eu": [{{"assertion": "string", "supporting_finding_ids": []}}],
    "russia": [{{"assertion": "string", "supporting_finding_ids": []}}],
    "neutral": [{{"assertion": "string", "supporting_finding_ids": []}}]
  }},
  "recommended_actions": ["string"],
  "information_gaps": ["string"]
}}"""


# ── MCP adapter functions ─────────────────────────────────────────────────────


def analysis_generate(
    pir: str,
    findings: str,
) -> str:
    """Prompt for synthesising processed findings into a structured intelligence analysis.

    Moved from AnalysisPrototypeService._build_prompt() — same content, now served
    via MCP so the backend fetches it through MCPClient instead of hardcoding it.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        findings: Processed findings JSON injected by the backend after reading
                  the session Resource (session://{session_id}/processed).
    """
    return build_analysis_generate_prompt(
        pir=pir,
        findings=findings,
    )
