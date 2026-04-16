def council_persona_us() -> str:
    """Council persona prompt for the US Strategic Analyst perspective.

    TODO: DB migration — replace hardcoded text with a query to
    knowledge.db: SELECT persona_prompt FROM perspectives WHERE id = 'us'
    """
    return (
        "Assess the issue from a US strategic perspective. Focus on alliance posture, "
        "deterrence, intelligence implications, and downstream operational risk."
    )


def council_persona_norway() -> str:
    """Council persona prompt for the Norway Security Analyst perspective.

    TODO: DB migration — replace hardcoded text with a query to
    knowledge.db: SELECT persona_prompt FROM perspectives WHERE id = 'norway'
    """
    return (
        "Assess the issue from a Norwegian national-security perspective. Focus on "
        "critical infrastructure resilience, regional stability, and practical defensive implications."
    )


def council_persona_china() -> str:
    """Council persona prompt for the China Strategic Analyst perspective.

    TODO: DB migration — replace hardcoded text with a query to
    knowledge.db: SELECT persona_prompt FROM perspectives WHERE id = 'china'
    """
    return (
        "Assess the issue from a China-focused strategic perspective. Focus on state interests, "
        "competitive positioning, economic exposure, and long-term leverage."
    )


def council_persona_eu() -> str:
    """Council persona prompt for the EU Policy Analyst perspective.

    TODO: DB migration — replace hardcoded text with a query to
    knowledge.db: SELECT persona_prompt FROM perspectives WHERE id = 'eu'
    """
    return (
        "Assess the issue from an EU strategic policy perspective. Focus on cross-border dependencies, "
        "collective resilience, regulatory implications, and bloc-level risk."
    )


def council_persona_russia() -> str:
    """Council persona prompt for the Russia Strategic Analyst perspective.

    TODO: DB migration — replace hardcoded text with a query to
    knowledge.db: SELECT persona_prompt FROM perspectives WHERE id = 'russia'
    """
    return (
        "Assess the issue from a Russia-focused strategic perspective. Focus on power projection, "
        "regional pressure, escalation dynamics, and asymmetric options."
    )


def council_persona_neutral() -> str:
    """Council persona prompt for the Neutral Evidence Analyst perspective.

    TODO: DB migration — replace hardcoded text with a query to
    knowledge.db: SELECT persona_prompt FROM perspectives WHERE id = 'neutral'
    """
    return (
        "Assess the issue neutrally. Prioritize evidence quality, explicit uncertainty, competing "
        "hypotheses, and alternative explanations before drawing conclusions."
    )
