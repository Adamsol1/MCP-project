"""Analysis phase prompt builders and MCP adapter functions.

AI #1 (generator) prompt for synthesising processed findings into an AnalysisDraft.
The corresponding AI #2 (reviewer) prompt lives in review_mcp_server/src/prompts/analysis.py.
"""


def build_analysis_generate_prompt(
    pir: str,
    findings: str,
    perspectives: str = "us, norway, china, eu, russia, neutral",
) -> str:
    # Build the per_perspective_implications schema dynamically from the selected list
    perspective_keys = [p.strip() for p in perspectives.split(",") if p.strip()]
    implications_example = "\n".join(
        f'    "{key}": [{{"assertion": "string — analytical implication from {key} viewpoint", "supporting_finding_ids": ["F-001"]}}]{"," if i < len(perspective_keys) - 1 else ""}'
        for i, key in enumerate(perspective_keys)
    )

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
- Title must be 6-10 words, written in intelligence-report style (e.g. "China-Taiwan Conflict Probability Assessment 2025"). Capitalise key words.
- Summary must be 2–4 sentences.
- Key judgments must be distinct and substantive — do not restate findings verbatim.
- Only generate per_perspective_implications for the following perspectives: {perspectives}
- For each perspective, provide as many implications as the evidence warrants.
- Each implication should be analytically substantive — develop the assertion fully rather than summarising it. Explain why it matters from this perspective, not just what the finding shows.
- Each implication must be traceable to specific findings; do not assert implications you cannot support.
- supporting_finding_ids must only contain finding IDs present in the findings above (e.g. "F-001").
- If an implication cannot be traced to a specific finding, use an empty array [].
- Recommended actions must be actionable and analyst-relevant.
- information_gaps must reflect the gaps listed in the findings — do not invent new ones.

## Output Format
Return ONLY valid JSON. No preamble, no explanation, no markdown fences.

{{
  "title": "string — 6-10 word intelligence assessment title",
  "summary": "string",
  "key_judgments": ["string"],
  "per_perspective_implications": {{
{implications_example}
  }},
  "recommended_actions": ["string"],
  "information_gaps": ["string"]
}}"""


# ── MCP adapter functions ─────────────────────────────────────────────────────


def analysis_generate(
    pir: str,
    findings: str,
    perspectives: str = "us, norway, china, eu, russia, neutral",
) -> str:
    """Prompt for synthesising processed findings into a structured intelligence analysis.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        findings: Processed findings JSON injected by the backend after reading
                  the session Resource (session://{session_id}/processed).
        perspectives: Comma-separated list of selected perspective keys to generate
                      implications for (e.g. "us, eu, neutral").
    """
    return build_analysis_generate_prompt(
        pir=pir,
        findings=findings,
        perspectives=perspectives,
    )
