"""Display name lookup for perspective-based analysis and council phases."""

from src.models.dialogue import Perspective

_DISPLAY_NAMES: dict[Perspective, str] = {
    Perspective.US: "US Strategic Analyst",
    Perspective.NORWAY: "Norway Security Analyst",
    Perspective.CHINA: "China Strategic Analyst",
    Perspective.EU: "EU Policy Analyst",
    Perspective.RUSSIA: "Russia Strategic Analyst",
    Perspective.NEUTRAL: "Neutral Evidence Analyst",
}

_DISPLAY_NAMES_BY_LANGUAGE: dict[str, dict[Perspective, str]] = {
    "en": _DISPLAY_NAMES,
    "no": {
        Perspective.US: "USA-analytiker",
        Perspective.NORWAY: "Norge-analytiker",
        Perspective.CHINA: "Kina-analytiker",
        Perspective.EU: "EU-analytiker",
        Perspective.RUSSIA: "Russland-analytiker",
        Perspective.NEUTRAL: "Nøytral bevisanalytiker",
    },
}


def get_display_name(perspective: Perspective, language: str = "en") -> str:
    table = _DISPLAY_NAMES_BY_LANGUAGE.get(language, _DISPLAY_NAMES)
    return table[perspective]
