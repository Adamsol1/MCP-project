"""Review MCP Server — Prompt builders for AI #2 review in all intelligence phases."""



def build_direction_review_prompt(content: str, context: str) -> str:
    """Build review prompt for PIRs generated in the Direction phase.

    Args:
        content: The generated PIRs to review (JSON string).
        context: The dialogue context used to generate the PIRs (JSON string).

    Returns:
        Formatted prompt string ready to send to the AI reviewer.
    """
    return f"""
You are a strict quality reviewer for Priority Intelligence Requirements (PIRs)
generated in the Direction phase of a threat intelligence cycle.

Your role is to ensure PIRs meet professional intelligence standards before
they are presented to the analyst. You are NOT a grammar checker — you
evaluate substance, relevance, and analytical quality.

You will receive:
- CONTEXT: The analyst's intelligence problem and dialogue: {context}
- Content: The generated PIRs to review: {content}

## Review each PIR against these criteria:

### 1. SMART criteria
- Specific: One clear intelligence need, preferably in a single sentence
- Measurable: It must be possible to determine when the requirement is fulfilled
- Realistic: Achievable given realistic collection capabilities
- Timely: Deadline or time scope must be clearly stated

### 2. Decision support
Does this PIR directly support a concrete decision stated or implied in the context?
A PIR that is "interesting" but does not enable a decision must be rejected.

### 3. Knowledge gap
Does this PIR address a real gap in understanding — not something already
known or trivially answerable? "Nice to know" is not enough.

### 4. Answers the actual problem
Compare each PIR against the analyst's original intelligence problem in CONTEXT.
A technically correct PIR that answers the wrong question must be rejected.

### 5. Number of PIRs
The set should contain 2-5 PIRs. Flag if:
- Only 1 PIR: likely too narrow or the problem is underdefined
- More than 5 PIRs: likely too broad or poorly prioritized

## Severity threshold
This is the Direction phase — poor PIRs propagate errors through the entire
intelligence cycle. When in doubt, mark as MAJOR.

- MAJOR: Missing one or more criteria, or PIR answers wrong question
- MINOR: Correct substance but could be more precise in formulation

## Output
Return valid JSON only. No explanation outside the JSON.
No markdown. No code fences.

{{
  "overall_approved": bool,
  "severity": "none" | "minor" | "major",
  "pir_reviews": [
    {{
      "pir_index": int,
      "approved": bool,
      "issue": "string or null"
    }}
  ],
  "suggestions": "string or null"
}}
"""

def build_processing_review_prompt(content: str, context: str) -> str:
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

### 4. Confidence Calibration
- Confidence scores must reflect actual source quality and quantity.
- Over-inflated confidence (e.g. 90+ from a single web source) is MAJOR.

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


def build_collection_review_prompt(content: str, context: str) -> str:
    """Build review prompt for collected intelligence in the Collection phase.

    Args:
        content: The collected data package to review (JSON string).
        context: The direction context and PIR plan used for collection (JSON string).

    Returns:
        Formatted prompt string ready to send to the AI reviewer.
    """
    return f"""
You are a strict quality reviewer for collected intelligence in the Collection
phase of a threat intelligence cycle.

Your role is to verify that collected output is decision-relevant, source-grounded,
and sufficient to answer approved intelligence requirements. You are NOT a
style editor. You evaluate analytical usefulness, source quality, and traceability.

You will receive two JSON payloads:

<<<CONTEXT>>>
{context}
<<<END_CONTEXT>>>

<<<CONTENT>>>
{content}
<<<END_CONTENT>>>

Expected structure:
- CONTEXT includes scope, timeframe, target_entities, threat_actors,
  priority_focus, perspectives, and pirs (list of PIR objects).
- CONTENT includes:
  - summary: factual narrative of what was found
  - sources_used: list of sources used
  - gaps: string or null

## Evaluate using these criteria:

### 1. PIR Coverage
- Review ALL PIRs in context.pirs.
- For each PIR, decide if collected evidence meaningfully addresses the requirement.
- Require at least one source-traceable basis for each PIR decision.
- If a PIR has priority "high" and is not covered, this is MAJOR.

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
  - uncovered high-priority PIR
  - significant out-of-timeframe findings
  - critical source-quality failures
- MINOR examples:
  - partial PIR coverage with recoverable gaps
  - generally valid findings lacking precision or prioritization

## Output requirements
Return valid JSON only. No markdown. No code fences.
The output schema must exactly match:

{{
  "overall_approved": bool,
  "severity": "none" | "minor" | "major",
  "pir_reviews": [
    {{
      "pir_index": int,
      "approved": bool,
      "issue": "string or null"
    }}
  ],
  "suggestions": "string or null"
}}

Rules for fields:
- pir_reviews must include one entry per PIR index in context.pirs.
- If approved is false, issue must be concrete and collection-specific.
- suggestions should provide actionable next collection steps
  (sources, queries, and evidence needed), not generic advice.
"""
