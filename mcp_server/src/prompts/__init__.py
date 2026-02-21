"""MCP Prompts - Workflow templates."""


def build_pir_generation_prompt(
    scope: str,
    timeframe: str,
    target_entities: list,
    perspectives: list,
    modifications: str | None = None,
) -> str:
    """Build prompt for PIR document generation."""
    entities_str = ", ".join(target_entities)
    perspectives_str = ", ".join(perspectives)
    modifications_block = ""
    if modifications:
        modifications_block = f"\nUSER REQUESTED MODIFICATIONS:\n{modifications}\n"

    return f"""You are a senior threat intelligence analyst. Generate a formal Priority Intelligence Requirement (PIR) document based on the following context.

INVESTIGATION CONTEXT:
- Scope: {scope}
- Timeframe: {timeframe}
- Target Entities: {entities_str}
- Analytical Perspectives: {perspectives_str}
{modifications_block}
PIR DOCUMENT STRUCTURE (use these exact section headers):
1. PIR Statement: One clear sentence stating the core intelligence need
2. Essential Elements of Information (EEIs): 3-5 specific questions the collection phase must answer
3. Collection Focus: Which source types are most relevant (OSINT, HUMINT, SIGINT, TECHINT, etc.)
4. Priority Level: HIGH / MEDIUM / LOW with a one-sentence justification
5. Success Criteria: How we will know when the PIR is satisfied

Generate a professional, actionable PIR document. Be specific — avoid vague language.
Return JSON:
{
    "result":"human readable result",
    "pirs":"list of all pirs that are created",
    "reasoning":"explain the logic used"
}

Respond ONLY in valid JSON.
No markdown.
No commentary.
"""
