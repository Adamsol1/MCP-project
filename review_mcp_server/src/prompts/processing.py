"""Processing phase review prompt builder and MCP adapter function."""


def build_processing_review_prompt(content: str, context: str) -> str:
    """Build review prompt for correlations produced in the Processing phase.

    Args:
        content: The correlation report to review (JSON string).
        context: The collected data used as input (JSON string).

    Returns:
        Formatted prompt string ready to send to the AI reviewer.
    """
    return f"""You are a strict quality reviewer for processing results produced in the Processing
phase of a threat intelligence cycle.

Your role is to verify that the PMESII entities extracted are grounded in the collected
evidence, correctly categorized, and relevant to the PIRs. You are NOT a grammar checker —
you evaluate analytical quality, evidence traceability, and PIR alignment.

<<<CONTEXT>>>
{context}
<<<END_CONTEXT>>>

<<<CONTENT>>>
{content}
<<<END_CONTENT>>>

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
- If PIRs remain unanswered after processing, gaps must reflect that.
- Empty gaps when PIRs are clearly unaddressed is MAJOR.

## Severity policy
- MAJOR: unsupported entity, missing high-priority PIR coverage, over-inflated confidence, missing critical gaps
- MINOR: minor categorization error, slightly imprecise confidence, low-priority gap omission

## Output
Return valid JSON only. No markdown. No code fences.

{{
  "overall_approved": bool,
  "severity": "none" | "minor" | "major",
  "pir_reviews": [
    {{
      "pir_index": 0,
      "approved": bool,
      "issue": "string or null"
    }}
  ],
  "suggestions": "string or null"
}}"""


# ── MCP adapter function ──────────────────────────────────────────────────────


def processing_review(content: str, context: str) -> str:
    """Review prompt for correlations produced in the Processing phase.

    Args:
        content: The correlation report to review (JSON string).
        context: The collected data used as input (JSON string).
    """
    return build_processing_review_prompt(content, context)
