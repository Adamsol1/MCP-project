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
    """Build review prompt for correlation report produced in the Processing phase.

    Args:
        content: The correlation report to review (JSON string).
        context: The collected data used as input (JSON string).

    Returns:
        Formatted prompt string ready to send to the AI reviewer.
    """
    return f"""
You are a strict quality reviewer for correlation reports produced in the Processing
phase of a threat intelligence cycle.

Your role is to verify that the correlation report correctly identifies patterns,
connections, and analytical conclusions grounded in the collected evidence. You are
NOT a grammar checker — you evaluate analytical rigor, logical soundness, and
evidence traceability.

You will receive two JSON payloads:

<<<CONTEXT>>>
{context}
<<<END_CONTEXT>>>

<<<CONTENT>>>
{content}
<<<END_CONTENT>>>

Expected structure:
- CONTEXT includes the collected intelligence: summary, sources_used, gaps, and PIRs.
- CONTENT includes:
  - correlations: list of identified patterns or connections
  - key_findings: highest-confidence analytical conclusions
  - confidence_level: overall confidence (high / medium / low)
  - gaps: unresolved analytical gaps or null

## Evaluate using these criteria:

### 1. Evidence Grounding
- Every correlation must be traceable to at least one source from context.sources_used.
- Unsupported correlations asserted as fact are MAJOR.
- Correlations based on a single weak source should be flagged MINOR unless central.

### 2. Logical Soundness
- Verify that connections between entities, events, or indicators follow logically.
- Reject conclusions that require unexplained leaps of logic (MAJOR).
- Flag over-confident conclusions where evidence only supports a weaker claim (MINOR).

### 3. PIR Alignment
- Key findings must contribute to answering at least one PIR from the context.
- A finding that is interesting but unrelated to any PIR should be flagged MINOR.
- If high-priority PIRs have no associated finding, flag as MAJOR.

### 4. Confidence Calibration
- Verify that overall confidence_level reflects the quality and quantity of evidence.
- Over-inflated confidence relative to evidence depth is MAJOR.

### 5. Gap Completeness
- If key analytical questions remain unanswered after processing, gaps must reflect that.
- gaps = null when important questions are unresolved is MAJOR.

## Severity policy
- MAJOR examples:
  - unsupported correlation stated as established fact
  - high-priority PIR with no associated key finding
  - over-inflated confidence relative to evidence
  - unexplained logical leap in a key conclusion
- MINOR examples:
  - valid finding with imprecise confidence framing
  - useful correlation that slightly exceeds the evidence basis
  - minor gap reporting omission on low-priority items

## Output requirements
Return valid JSON only. No markdown. No code fences.
The output schema must exactly match:

{{
  "overall_approved": bool,
  "severity": "none" | "minor" | "major",
  "correlation_reviews": [
    {{
      "correlation_index": int,
      "approved": bool,
      "issue": "string or null"
    }}
  ],
  "suggestions": "string or null"
}}

Rules for fields:
- correlation_reviews must include one entry per correlation in content.correlations.
- If approved is false, issue must be specific and evidence-based.
- suggestions should provide actionable guidance for strengthening the analysis.
"""


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
