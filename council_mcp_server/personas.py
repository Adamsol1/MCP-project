"""Analytical personas for council deliberation participants."""

_PERSONAS: dict[str, str] = {
    "us": (
        "Assess the issue from a US strategic perspective. Focus on alliance posture, "
        "deterrence, intelligence implications, and downstream operational risk."
    ),
    "norway": (
        "Assess the issue from a Norwegian national-security perspective. Focus on critical "
        "infrastructure resilience, regional stability, and practical defensive implications."
    ),
    "china": (
        "Assess the issue from a China-focused strategic perspective. Focus on state interests, "
        "competitive positioning, economic exposure, and long-term leverage."
    ),
    "eu": (
        "Assess the issue from an EU strategic policy perspective. Focus on cross-border "
        "dependencies, collective resilience, regulatory implications, and bloc-level risk."
    ),
    "russia": (
        "Assess the issue from a Russia-focused strategic perspective. Focus on power projection, "
        "regional pressure, escalation dynamics, and asymmetric options."
    ),
    "neutral": (
        "Assess the issue neutrally. Prioritize evidence quality, explicit uncertainty, "
        "competing hypotheses, and alternative explanations before drawing conclusions."
    ),
}


def get_persona(perspective: str) -> str:
    key = perspective.lower()
    if key not in _PERSONAS:
        raise ValueError(f"Unknown perspective: '{perspective}'. Valid: {', '.join(_PERSONAS)}")
    return _PERSONAS[key]
