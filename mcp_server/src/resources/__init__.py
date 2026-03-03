"""MCP Resources - Knowledge bank registry and loader."""

from pathlib import Path

RESOURCES_DIR = Path(__file__).parent

KNOWLEDGE_REGISTRY: dict[str, dict] = {
    # ── Geopolitical relationships ──────────────────────────────────────────
    "geopolitical/norway_russia": {
        "keywords": ["norway", "norwegian", "svalbard", "arctic", "russian"],
        "priority": 1,
    },
    "geopolitical/norway_china": {
        "keywords": ["norway", "norwegian", "chinese", "huawei",
                     "belt and road", "belt road", "bri", "new silk road", "obor"],
        "priority": 1,
    },
    "geopolitical/eu_russia": {
        "keywords": ["european union", "eu", "russian", "gazprom", "nord stream"],
        "priority": 1,
    },
    "geopolitical/eu_usa": {
        "keywords": ["european union", "eu", "american", "transatlantic", "nato"],
        "priority": 1,
    },
    "geopolitical/eu_china": {
        "keywords": ["european union", "eu", "chinese",
                     "belt and road", "belt road", "bri", "new silk road", "obor"],
        "priority": 1,
    },
    "geopolitical/usa_china": {
        "keywords": ["american", "usa", "chinese", "taiwan", "trade war",
                     "belt and road", "belt road", "bri", "new silk road", "obor"],
        "priority": 1,
    },
    "geopolitical/usa_russia": {
        "keywords": ["american", "usa", "russian", "nato", "sanctions"],
        "priority": 1,
    },
    # ── Sectors ─────────────────────────────────────────────────────────────
    "sectors/energy": {
        "keywords": ["energy", "oil", "gas", "pipeline", "lng"],
        "priority": 2,
    },
    "sectors/financial": {
        "keywords": ["financial", "banking", "swift", "central bank"],
        "priority": 2,
    },
    "sectors/telecommunications": {
        "keywords": ["telecom", "5g", "telecommunications", "undersea cable"],
        "priority": 2,
    },
    # ── Threat actors ────────────────────────────────────────────────────────
    "threat_actors/russian_state": {
        "keywords": ["apt28", "sandworm", "cozy bear", "fsb", "gru", "svr"],
        "priority": 3,
    },
    "threat_actors/chinese_state": {
        "keywords": ["apt41", "volt typhoon", "mss", "double dragon"],
        "priority": 3,
    },
}


def load_knowledge(scan_text: str) -> str | None:
    """Match keywords against scan_text and return formatted content from top 5 matches.

    Args:
        scan_text: Free-form text derived from investigation context fields.

    Returns:
        Formatted background knowledge string with source headers, or None if no matches.
    """
    if not scan_text.strip():
        return None

    text_lower = scan_text.lower()
    matches: dict[str, dict] = {}

    for resource_id, entry in KNOWLEDGE_REGISTRY.items():
        for keyword in entry["keywords"]:
            if keyword.lower() in text_lower:
                matches[resource_id] = entry
                break

    if not matches:
        return None

    sorted_entries = sorted(matches.items(), key=lambda x: x[1]["priority"])[:5]

    content = ["## Background Knowledge"]
    for resource_id, _ in sorted_entries:
        path = RESOURCES_DIR / f"{resource_id}.md"
        try:
            content.append(f"### Source: {resource_id}")
            content.append(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue

    return "\n".join(content) if len(content) > 1 else None
