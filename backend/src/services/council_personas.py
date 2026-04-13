"""Mapping from app perspectives to reusable council participant personas."""

from pydantic import BaseModel, Field

from src.models.dialogue import Perspective


class CouncilPersonaConfig(BaseModel):
    """User-facing council persona configuration."""

    display_name: str = Field(..., description="App-facing participant display name")
    persona_prompt: str = Field(
        ...,
        description="Participant-specific analytical instruction for council debate",
    )


_COUNCIL_PERSONAS: dict[Perspective, CouncilPersonaConfig] = {
    Perspective.US: CouncilPersonaConfig(
        display_name="US Strategic Analyst",
        persona_prompt=(
            "Assess the issue from a US strategic perspective. Focus on alliance posture, "
            "deterrence, intelligence implications, and downstream operational risk."
        ),
    ),
    Perspective.NORWAY: CouncilPersonaConfig(
        display_name="Norway Security Analyst",
        persona_prompt=(
            "Assess the issue from a Norwegian national-security perspective. Focus on "
            "critical infrastructure resilience, regional stability, and practical defensive implications."
        ),
    ),
    Perspective.CHINA: CouncilPersonaConfig(
        display_name="China Strategic Analyst",
        persona_prompt=(
            "Assess the issue from a China-focused strategic perspective. Focus on state interests, "
            "competitive positioning, economic exposure, and long-term leverage."
        ),
    ),
    Perspective.EU: CouncilPersonaConfig(
        display_name="EU Policy Analyst",
        persona_prompt=(
            "Assess the issue from an EU strategic policy perspective. Focus on cross-border dependencies, "
            "collective resilience, regulatory implications, and bloc-level risk."
        ),
    ),
    Perspective.RUSSIA: CouncilPersonaConfig(
        display_name="Russia Strategic Analyst",
        persona_prompt=(
            "Assess the issue from a Russia-focused strategic perspective. Focus on power projection, "
            "regional pressure, escalation dynamics, and asymmetric options."
        ),
    ),
    Perspective.NEUTRAL: CouncilPersonaConfig(
        display_name="Neutral Evidence Analyst",
        persona_prompt=(
            "Assess the issue neutrally. Prioritize evidence quality, explicit uncertainty, competing "
            "hypotheses, and alternative explanations before drawing conclusions."
        ),
    ),
}


def get_council_persona(
    perspective: str | Perspective,
) -> CouncilPersonaConfig:
    """Return the council persona configuration for a supported app perspective."""
    normalized = (
        perspective if isinstance(perspective, Perspective) else Perspective(perspective.lower())
    )

    try:
        return _COUNCIL_PERSONAS[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported perspective: {perspective}") from exc


def list_council_personas() -> dict[str, CouncilPersonaConfig]:
    """Return all supported council persona mappings keyed by perspective value."""
    return {perspective.value: config for perspective, config in _COUNCIL_PERSONAS.items()}
