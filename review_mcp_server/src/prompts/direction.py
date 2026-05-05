"""Direction phase review prompt builder and MCP adapter function."""

from datetime import UTC, datetime


def build_direction_review_prompt(content: str, context: str) -> str:
    _today = datetime.now(UTC).strftime('%Y-%m-%d')

    return f"""You are a strict quality reviewer for Priority Intelligence Requirements (PIRs)
generated in the Direction phase of a threat intelligence cycle.

TODAY'S DATE: {_today}
Use this as the reference point for all temporal reasoning, including timeliness assessments.

Your role is to ensure PIRs meet professional intelligence standards before
they are presented to the analyst. You are NOT a grammar checker — you
evaluate substance, relevance, and analytical quality.

## Intelligence Context
{context}

## PIRs to Review
{content}

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
Compare each PIR against the analyst's original intelligence problem in the context above.
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
  "suggestions": "string — use JSON null (not the string 'null') if no suggestions"
}}"""


# ── MCP adapter function ──────────────────────────────────────────────────────


def direction_review(content: str, context: str) -> str:
    """Review prompt for PIRs generated in the Direction phase.

    Args:
        content: The generated PIRs to review (JSON string).
        context: The dialogue context used to generate the PIRs (JSON string).
    """
    return build_direction_review_prompt(content, context)
