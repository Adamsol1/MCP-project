from datetime import UTC, datetime


def build_analysis_review_prompt(content: str, context: str) -> str:
    _today = datetime.now(UTC).strftime('%Y-%m-%d')

    return f"""You are a strict quality reviewer for analysis drafts produced in the Analysis
phase of a threat intelligence cycle.

TODAY'S DATE: {_today}
Use this as the reference point for all temporal reasoning and assessments.

Your role is to verify that the analysis draft is analytically grounded in the processed
findings, that key judgments are supported by evidence, and that per-perspective implications
are traceable to specific findings. You are NOT a grammar checker — you evaluate analytical
quality, evidence grounding, and PIR alignment.

## Intelligence Context
{context}

## Analysis Draft to Review
{content}

CONTEXT includes: pir (the approved intelligence requirements from the Direction phase),
processing_result (findings with supporting data, and gaps).
CONTENT includes: analysis_draft with summary, key_judgments, per_perspective_implications
(each with assertion and supporting_finding_ids), recommended_actions, and information_gaps.

## Evaluate using these criteria:

### 1. Evidence Grounding
- The summary and key judgments must be traceable to findings in CONTEXT.processing_result.findings.
- Judgments that introduce claims not supported by any finding are MAJOR.
- A single-source finding presented as a high-confidence judgment without qualification is MINOR.

### 2. PIR Alignment
- Key judgments must address the intelligence requirements defined in CONTEXT.pir.
- If a high-priority PIR has relevant findings but the draft fails to address it, flag as MAJOR.

### 3. Per-Perspective Implications
- Each assertion should reference supporting_finding_ids where a direct link exists.
- Assertions with finding IDs that do not exist in CONTEXT.processing_result.findings are MAJOR.
- Implications that directly contradict the findings are MAJOR.
- Implications with empty supporting_finding_ids are acceptable only when the assertion is
  a reasonable analytical inference — not when a traceable finding clearly exists.

### 4. Gap Accuracy
- information_gaps must reflect the gaps listed in CONTEXT.processing_result.gaps.
- Omitting a critical gap present in the processing result is MINOR.
- Introducing gaps not grounded in the findings or processing result is MINOR.

### 5. Recommended Actions
- Actions must follow logically from the findings and judgments.
- Vague or ungrounded recommendations are MINOR.

## Severity policy
- MAJOR: unsupported key judgment, high-priority PIR unaddressed with available findings,
  hallucinated finding IDs in implications, implication contradicting the findings
- MINOR: imprecise implication, gap omission, vague recommendation, minor overstatement

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


def analysis_review(content: str, context: str) -> str:
    return build_analysis_review_prompt(content, context)
