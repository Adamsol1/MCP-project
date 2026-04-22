"""MCP Resources - Knowledge bank registry and loader."""

import json
import logging
from pathlib import Path

from models import PIRResponse

logger = logging.getLogger("mcp_server")

RESOURCES_DIR = Path(__file__).parent

KNOWLEDGE_REGISTRY: dict[str, dict] = {
    # ── Geopolitical relationships ──────────────────────────────────────────
    "geopolitical/norway_russia": {
        "keywords": ["norway", "norwegian", "svalbard", "arctic", "russian", "russia"],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "Norwegian-Russian Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "geopolitical/norway_china": {
        "keywords": ["norway", "norwegian", "chinese", "china", "huawei",
                     "belt and road", "belt road", "bri", "new silk road", "obor"],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "Norwegian-Chinese Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "geopolitical/eu_russia": {
        "keywords": ["european union", "eu", "russian", "russia", "gazprom", "nord stream"],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "EU-Russian Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "geopolitical/eu_usa": {
        "keywords": ["european union", "eu", "american", "transatlantic", "nato"],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "EU-United States Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "geopolitical/eu_china": {
        "keywords": ["european union", "eu", "chinese", "china",
                     "belt and road", "belt road", "bri", "new silk road", "obor"],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "EU-Chinese Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "geopolitical/usa_china": {
        "keywords": ["american", "usa", "united states", "chinese", "china", "taiwan", "trade war",
                     "belt and road", "belt road", "bri", "new silk road", "obor"],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "United States-Chinese Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "geopolitical/usa_russia": {
        "keywords": ["american", "usa", "united states", "russian", "russia", "nato", "sanctions"],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "United States-Russian Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
    # ── Sectors ─────────────────────────────────────────────────────────────
    "sectors/energy": {
        "keywords": ["energy", "oil", "gas", "pipeline", "lng"],
        "priority": 2,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "Energy Sector Threat Landscape",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "sectors/financial": {
        "keywords": ["financial", "banking", "swift", "central bank"],
        "priority": 2,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "Financial Sector Threat Landscape",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "sectors/telecommunications": {
        "keywords": ["telecom", "5g", "telecommunications", "undersea cable"],
        "priority": 2,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "Telecommunications Sector Threat Landscape",
            "publisher": "Internal Knowledge Bank",
        },
    },
    # ── Threat actors ────────────────────────────────────────────────────────
    "threat_actors/russian_state": {
        "keywords": ["apt28", "sandworm", "cozy bear", "fsb", "gru", "svr", "russia", "russian"],
        "priority": 3,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "Russian State-Sponsored Threat Actors",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "threat_actors/chinese_state": {
        "keywords": ["apt41", "volt typhoon", "mss", "double dragon", "china", "chinese"],
        "priority": 3,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "Chinese State-Sponsored Threat Actors",
            "publisher": "Internal Knowledge Bank",
        },
    },
}


def _load_knowledge_from_db(scan_text: str) -> str | None:
    """DB-backed keyword search — returns formatted markdown or None."""
    try:
        from db import get_knowledge_connection
        conn = get_knowledge_connection()
    except Exception:
        return None  # DB not available, caller falls back to file-based

    try:
        rows = conn.execute(
            "SELECT id, keywords, priority, markdown_content FROM knowledge_resources"
        ).fetchall()
    except Exception:
        conn.close()
        return None

    text_lower = scan_text.lower()
    scored: list[tuple[int, dict]] = []

    for row in rows:
        keywords = json.loads(row["keywords"]) if row["keywords"] else []
        hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        if hits > 0:
            scored.append((hits, {"id": row["id"], "priority": row["priority"], "content": row["markdown_content"]}))

    conn.close()

    if not scored:
        return None

    scored.sort(key=lambda x: (-x[0], x[1]["priority"]))
    top = scored[:5]

    content = ["## Background Knowledge"]
    for _, entry in top:
        content.append(f"### Source: {entry['id']}")
        content.append(entry["content"])

    return "\n".join(content) if len(content) > 1 else None


def _get_citation_from_db(resource_id: str) -> dict | None:
    """Look up citation for a resource from knowledge.db."""
    try:
        from db import get_knowledge_connection
        conn = get_knowledge_connection()
        row = conn.execute(
            "SELECT citation FROM knowledge_resources WHERE id = ?",
            (resource_id,),
        ).fetchone()
        conn.close()
        if row and row["citation"]:
            return json.loads(row["citation"])
    except Exception:
        pass
    return None


def load_knowledge(scan_text: str) -> str | None:
    """Match keywords against scan_text and return formatted content from top 5 matches.

    Tries knowledge.db first, falls back to file-based if DB is unavailable.

    Args:
        scan_text: Free-form text derived from investigation context fields.

    Returns:
        Formatted background knowledge string with source headers, or None if no matches.
    """
    if not scan_text.strip():
        return None

    # Try DB first
    db_result = _load_knowledge_from_db(scan_text)
    if db_result is not None:
        return db_result

    # Fallback: file-based
    logger.debug("knowledge.db unavailable, falling back to file-based knowledge loading")
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


def enrich_pir_response(raw_json: str) -> PIRResponse:
    """Parse raw AI JSON and enrich sources with citation metadata.

    Tries knowledge.db for citations first, falls back to KNOWLEDGE_REGISTRY.

    Args:
        raw_json: Raw JSON string from the AI's PIR generation response.

    Returns:
        Validated PIRResponse with full citation metadata attached to each source.

    Raises:
        ValueError: If raw_json is not valid JSON or doesn't match PIRResponse schema.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON: {e}") from e

    enriched_sources = []
    for source in data.get("sources", []):
        source_id = source.get("id", "")
        # Try DB first, then registry
        citation = _get_citation_from_db(source_id)
        if citation is None and source_id in KNOWLEDGE_REGISTRY:
            citation = KNOWLEDGE_REGISTRY[source_id].get("citation")
        if citation:
            source["citation"] = citation
            enriched_sources.append(source)
        # unknown source_id: silently drop

    data["sources"] = enriched_sources

    try:
        return PIRResponse.model_validate(data)
    except Exception as e:
        raise ValueError(f"invalid PIR response structure: {e}") from e

