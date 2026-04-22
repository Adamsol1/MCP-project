"""Analysis phase prompt builders and MCP adapter functions.

AI #1 (generator) prompt for synthesising processed findings into an AnalysisDraft.
The corresponding AI #2 (reviewer) prompt lives in review_mcp_server/src/prompts/analysis.py.
"""

from datetime import UTC, datetime

from ._shared import _language_instruction

# Analytical lens per perspective — mirrors council_mcp_server/personas.py.
# Tells the model what angle and themes to pursue when writing the `analysis` field.
_PERSPECTIVE_LENS: dict[str, str] = {
    "us": (
        "Focus on alliance posture, deterrence credibility, intelligence implications, "
        "escalation thresholds, and downstream operational risk to US interests and partners."
    ),
    "norway": (
        "Focus on critical infrastructure resilience, Arctic and Nordic regional stability, "
        "NATO obligations, and practical defensive implications for Norwegian security."
    ),
    "china": (
        "Focus on state interests and CPC legitimacy, competitive positioning, economic "
        "exposure and leverage, long-term strategic goals, and how this shifts the balance "
        "of power or opens windows of opportunity."
    ),
    "eu": (
        "Focus on cross-border dependencies, collective resilience, regulatory and sanctions "
        "implications, bloc-level risk, and internal cohesion challenges among member states."
    ),
    "russia": (
        "Focus on power projection, regional pressure dynamics, escalation options, "
        "asymmetric tools, and how this shifts Russia's coercive leverage or exposes vulnerabilities."
    ),
    "neutral": (
        "Prioritise evidence quality and explicit uncertainty. Surface competing hypotheses "
        "and alternative explanations before drawing conclusions. Flag where assessments "
        "outrun the evidence."
    ),
}


def build_analysis_generate_prompt(
    pir: str,
    findings: str,
    perspectives: str = "us, norway, china, eu, russia, neutral",
    language: str = "en",
) -> str:
    _today = datetime.now(UTC).strftime('%Y-%m-%d')
    lang_note = _language_instruction(language, "all output fields")

    perspective_keys = [p.strip() for p in perspectives.split(",") if p.strip()]

    lens_lines = "\n".join(
        f"  - {key}: {_PERSPECTIVE_LENS.get(key, 'Assess from this perspective.')}"
        for key in perspective_keys
    )

    def _implication_line(i: int, key: str) -> str:
        lens = _PERSPECTIVE_LENS.get(key, "Assess from this perspective.")
        comma = "," if i < len(perspective_keys) - 1 else ""
        return (
            f'    "{key}": [{{'
            f'"assertion": "one-sentence headline claim from the {key} viewpoint", '
            f'"analysis": "analytical narrative written as a {key} analyst would. '
            f"Lens: {lens} "
            f'Cover why it matters, strategic and operational consequences, second-order effects, '
            f'how it shifts the {key} risk picture or decision calculus, and caveats. '
            f'Plain flowing prose, no bullet points, no headers.", '
            f'"supporting_finding_ids": ["F-001"]}}'
            f"]]{comma}"
        )

    implications_example = "\n".join(
        _implication_line(i, key) for i, key in enumerate(perspective_keys)
    )

    return f"""{lang_note}You are drafting an intelligence-analysis summary for an analyst UI.

TODAY'S DATE: {_today}
Use this as the reference point for all temporal reasoning and assessments.

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

## Per-Perspective Analytical Lens
Write each `analysis` field through the lens of the respective perspective's priorities:
{lens_lines}

## Writing the `analysis` field
Each implication has two parts:
- `assertion`: one-sentence headline claim — what is true from this perspective
- `analysis`: deep analytical narrative grounded in the findings. Write as the perspective's analyst would. Explain WHY it matters, what strategic or operational consequences follow, how it changes the actor's risk picture or decision calculus, second-order effects, and caveats. Use plain flowing prose — no bullet points or headers. Develop the argument fully; do not summarise or list.

- Each implication must be traceable to specific findings. If an implication cannot be traced to any finding, omit it entirely.
- supporting_finding_ids must only contain finding IDs present in the findings above (e.g. "F-001").
- Recommended actions must be actionable and analyst-relevant.
- information_gaps must only contain gaps explicitly stated in the findings. Copy them faithfully — do not paraphrase, expand, or add new ones.

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
