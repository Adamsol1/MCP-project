"""Collection phase review prompt builder and MCP adapter function."""

import json as _json
from datetime import UTC, datetime


def build_collection_review_prompt(content: str, context: str) -> str:
    _today = datetime.now(UTC).strftime('%Y-%m-%d')

    try:
        _ctx = _json.loads(context)
        _gather_more_feedback = (_ctx.get("gather_more_feedback") or "").strip()
    except Exception:
        _gather_more_feedback = ""

    if _gather_more_feedback:
        _mode_header = f"""
## SUPPLEMENTAL COLLECTION MODE
This is an **incremental** "gather more" run — NOT the initial full collection.
The user requested additional data to address a specific gap:
> {_gather_more_feedback}

Evaluate ONLY whether the new collected data meaningfully addresses this gap request.
Do NOT require full coverage of all PIRs — prior collection runs already addressed
the base requirements. Apply the following adjusted criteria:
- PIR Coverage: approve a PIR if the new data adds relevant evidence toward the gap.
  Only flag MAJOR if the new data is entirely irrelevant to the stated gap.
- Source Quality, Traceability, and Timeframe rules still apply normally.
- Do not penalize for limited breadth — supplemental runs are expected to be narrower.

"""
        _pir_coverage_rule = (
            "- This is a supplemental run. Evaluate each PIR only in relation to the "
            "stated gap above. Approve if the new data adds at least partial value. "
            "Only flag MAJOR if the new data completely fails to address the gap."
        )
    else:
        _mode_header = ""
        _pir_coverage_rule = (
            "- Review ALL PIRs in context.pirs.\n"
            "- For each PIR, decide if collected evidence meaningfully addresses the requirement.\n"
            "- Require at least one source-traceable basis for each PIR decision.\n"
            "- If a PIR has priority \"high\" and is not covered, this is MAJOR."
        )

    return f"""You are a strict quality reviewer for collected intelligence in the Collection
phase of a threat intelligence cycle.

TODAY'S DATE: {_today}
Use this as the reference point for all temporal reasoning, including timeframe compliance assessments.

Your role is to verify that collected output is decision-relevant, source-grounded,
and sufficient to answer approved intelligence requirements. You are NOT a
style editor. You evaluate analytical usefulness, source quality, and traceability.
{_mode_header}
## Intelligence Context
{context}

## Collected Output to Review
{content}

Expected structure:
- CONTEXT includes scope, timeframe, target_entities, threat_actors,
  priority_focus, perspectives, and pirs (list of PIR objects).
- CONTENT includes:
  - summary: factual narrative of what was found
  - sources_used: list of sources used
  - gaps: string or null

## Evaluate using these criteria:

### 1. PIR Coverage
{_pir_coverage_rule}

### 2. Source Quality
- Check relevance: sources must match the PIR and target context.
- Check credibility: sources should be reasonably trustworthy.
- Check recency: sources and findings must align with context.timeframe.

### 3. Gaps Realism
- gaps = null means "no known gaps".
- If PIR coverage is weak or partial and gaps is null, flag missing gap reporting.
- If gaps is present, check that it reflects realistic unresolved questions.

### 4. Traceability / Hallucination
- Enforce strict claim traceability.
- Material claims in summary must be supportable by sources_used.
- Unsupported material claims are MAJOR.

### 5. Timeframe Compliance
- Treat significant out-of-timeframe evidence as MAJOR.
- If timeframe violations are present, require explicit correction guidance.

## Severity policy
When in doubt, be strict because weak collection quality propagates errors downstream.

- MAJOR examples:
  - unsupported material claims
  - uncovered high-priority PIR (full collection mode only)
  - significant out-of-timeframe findings
  - critical source-quality failures
  - supplemental run that adds zero relevant data for the stated gap
- MINOR examples:
  - partial PIR coverage with recoverable gaps
  - generally valid findings lacking precision or prioritization

## Output
Return valid JSON only. No markdown. No code fences.

Set overall_approved to true only if ALL individual PIRs are approved.

{{
  "overall_approved": bool,
  "severity": "none" | "minor" | "major",
  "pir_reviews": [
    {{
      "pir_index": int,
      "approved": bool,
      "issue": "string — use JSON null (not the string 'null') if no issue"
    }}
  ],
  "suggestions": "string — when overall_approved is true, write a brief justification explaining which criteria were met and why the collection is considered sufficient. Use JSON null (not the string 'null') only when overall_approved is false and no actionable guidance applies."
}}"""


# ── MCP adapter function ──────────────────────────────────────────────────────


def collection_review(content: str, context: str) -> str:
    """Review prompt for data collected in the Collection phase.

    Args:
        content: The collected data summary to review (JSON string).
        context: The collection plan and PIRs used as basis (JSON string).
    """
    return build_collection_review_prompt(content, context)
