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


def get_display_name(perspective: Perspective) -> str:
    return _DISPLAY_NAMES[perspective]
