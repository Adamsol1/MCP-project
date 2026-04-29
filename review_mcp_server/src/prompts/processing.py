"""Processing phase review prompt builder and MCP adapter function."""

import json as _json
from datetime import UTC, datetime


def build_processing_review_prompt(content: str, context: str) -> str:
    _today = datetime.now(UTC).strftime('%Y-%m-%d')

    try:
        _ctx = _json.loads(context)
        _is_revision = bool(_ctx.get("is_revision", False))
    except Exception:
        _is_revision = False

    if _is_revision:
        _mode_header = """
## RE-PROCESSING MODE
This is a **refinement** of an earlier processing result — not a fresh extraction.
The new result reflects updated or accumulated collected data building on prior work.

Apply these adjusted criteria:
- Gaps acknowledged as unresolvable in the previous result may legitimately persist.
  Do not penalize for gaps that were already present and correctly documented.
- Evaluate whether entities from the prior result have been correctly retained,
  updated, or removed based on the new collected data.
- Only flag MAJOR if the new result introduces unsupported entities, removes
  previously well-grounded entities without justification, or degrades PIR coverage
  compared to the prior result.

"""
        _gap_rule = (
            "- Gaps that appeared in the previous result and remain genuinely unresolvable "
            "are acceptable. Only flag MAJOR for gaps that are newly absent when PIRs are "
            "clearly still unaddressed by the new collected data."
        )
    else:
        _mode_header = ""
        _gap_rule = (
            "- If PIRs remain unanswered after processing, gaps must reflect that.\n"
            "- Empty gaps when PIRs are clearly unaddressed is MAJOR."
        )

    return f"""You are a strict quality reviewer for processing results produced in the Processing
phase of a threat intelligence cycle.

TODAY'S DATE: {_today}
Use this as the reference point for all temporal reasoning and timeframe assessments.

Your role is to verify that the PMESII entities extracted are grounded in the collected
evidence, correctly categorized, and relevant to the PIRs. You are NOT a grammar checker —
you evaluate analytical quality, evidence traceability, and PIR alignment.
{_mode_header}
## Intelligence Context
{context}

## Processing Result to Review
{content}

CONTEXT includes: pir (the intelligence requirements), collected_data (raw collected text).
CONTENT includes: entities (PMESIIEntity list), gaps, processing_summary, assessment_changed, change_summary.

## Evaluate using these criteria:

### 1. Evidence Grounding
- Every entity must be traceable to the collected_data in CONTEXT.
- Entities not present in or derivable from the collected data are MAJOR.

### 2. PMESII Categorization
- Verify categories are correct for each entity (political, military, economic, social, information, infrastructure).
- Wrong categorization is MINOR unless it materially affects the analysis.

### 3. PIR Alignment
- Entities must be relevant to at least one PIR from CONTEXT.pir.
- If a high-priority PIR has no associated entities, flag as MAJOR.

### 4. Confidence Calibration (Algorithm-Computed)
- The system computes confidence algorithmically from source type, corroboration, and independence.
  Each finding may carry a `computed_confidence` field with `tier`, `score`, `authority`,
  `corroboration`, `independence`, and `circular_flag`.
- Flag as MAJOR if `computed_confidence.tier` is HIGH or ASSESSED but the finding has only
  one source type (single-source claim presented as strongly supported).
- Flag as MAJOR if `computed_confidence.circular_flag` is true but `tier` is above MODERATE
  (circular reporting should not yield high confidence).
- If `computed_confidence` is absent, fall back to checking the AI-generated `confidence`
  integer: over-inflated values (e.g. 90+ from a single web source) are MAJOR.

### 5. Gap Completeness
{_gap_rule}

## Severity policy
- MAJOR: unsupported entity, missing high-priority PIR coverage, over-inflated confidence, missing critical gaps
- MINOR: minor categorization error, slightly imprecise confidence, low-priority gap omission

## Output
Return valid JSON only. No markdown. No code fences.

Set overall_approved to true only if ALL individual PIRs are approved.

{{
  "overall_approved": bool,
  "severity": "none" | "minor" | "major",
  "pir_reviews": [
    {{
      "pir_index": 0,
      "approved": bool,
      "issue": "string — use JSON null (not the string 'null') if no issue"
    }}
  ],
  "suggestions": "string — use JSON null (not the string 'null') if no suggestions"
}}"""


# ── MCP adapter function ──────────────────────────────────────────────────────


def processing_review(content: str, context: str) -> str:
    """Review prompt for correlations produced in the Processing phase.

    Args:
        content: The correlation report to review (JSON string).
        context: The collected data used as input (JSON string).
    """
    return build_processing_review_prompt(content, context)
