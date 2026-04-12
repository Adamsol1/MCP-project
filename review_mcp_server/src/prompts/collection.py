"""Collection phase review prompt builder and MCP adapter function."""


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


# ── MCP adapter function ──────────────────────────────────────────────────────


def collection_review(content: str, context: str) -> str:
    """Review prompt for data collected in the Collection phase.

    Args:
        content: The collected data summary to review (JSON string).
        context: The collection plan and PIRs used as basis (JSON string).
    """
    return build_collection_review_prompt(content, context)
