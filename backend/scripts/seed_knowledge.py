"""Seed knowledge.db with data from the MCP server's .md resource files.

Reads the KNOWLEDGE_REGISTRY from mcp_server/src/resources/__init__.py
(duplicated here to avoid import-path gymnastics) and each corresponding
.md file, then upserts every row into knowledge.db.

Usage:
    cd backend
    python scripts/seed_knowledge.py
"""

import json
import sqlite3
import sys
from datetime import datetime, UTC
from pathlib import Path

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_ROOT.parent
RESOURCES_DIR = PROJECT_ROOT / "mcp_server" / "src" / "resources"
DATA_DIR = BACKEND_ROOT / "data"


# Inline copy of the registry (avoids importing from mcp_server which has its own deps)
KNOWLEDGE_REGISTRY: dict[str, dict] = {
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
        "keywords": [
            "norway",
            "norwegian",
            "chinese",
            "china",
            "huawei",
            "belt and road",
            "belt road",
            "bri",
            "new silk road",
            "obor",
        ],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "Norwegian-Chinese Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "geopolitical/eu_russia": {
        "keywords": [
            "european union",
            "eu",
            "russian",
            "russia",
            "gazprom",
            "nord stream",
        ],
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
        "keywords": [
            "european union",
            "eu",
            "chinese",
            "china",
            "belt and road",
            "belt road",
            "bri",
            "new silk road",
            "obor",
        ],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "EU-Chinese Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "geopolitical/usa_china": {
        "keywords": [
            "american",
            "usa",
            "united states",
            "chinese",
            "china",
            "taiwan",
            "trade war",
            "belt and road",
            "belt road",
            "bri",
            "new silk road",
            "obor",
        ],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "United States-Chinese Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "geopolitical/usa_russia": {
        "keywords": [
            "american",
            "usa",
            "united states",
            "russian",
            "russia",
            "nato",
            "sanctions",
        ],
        "priority": 1,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "United States-Russian Geopolitical Relations",
            "publisher": "Internal Knowledge Bank",
        },
    },
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
    "threat_actors/russian_state": {
        "keywords": [
            "apt28",
            "sandworm",
            "cozy bear",
            "fsb",
            "gru",
            "svr",
            "russia",
            "russian",
        ],
        "priority": 3,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "Russian State-Sponsored Threat Actors",
            "publisher": "Internal Knowledge Bank",
        },
    },
    "threat_actors/chinese_state": {
        "keywords": [
            "apt41",
            "volt typhoon",
            "mss",
            "double dragon",
            "china",
            "chinese",
        ],
        "priority": 3,
        "citation": {
            "author": "Threat Intelligence System",
            "year": "2025",
            "title": "Chinese State-Sponsored Threat Actors",
            "publisher": "Internal Knowledge Bank",
        },
    },
}


def seed() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_path = DATA_DIR / "knowledge.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    # Ensure table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_resources (
            id          TEXT PRIMARY KEY,
            category    TEXT NOT NULL DEFAULT '',
            keywords    TEXT NOT NULL DEFAULT '[]',
            priority    INTEGER NOT NULL DEFAULT 1,
            markdown_content TEXT NOT NULL DEFAULT '',
            citation    TEXT,
            last_updated DATETIME NOT NULL
        )
    """)

    now = datetime.now(UTC).isoformat()
    inserted = 0
    skipped = 0

    for resource_id, meta in KNOWLEDGE_REGISTRY.items():
        md_path = RESOURCES_DIR / f"{resource_id}.md"
        if not md_path.exists():
            print(f"  SKIP {resource_id} — .md file not found at {md_path}")
            skipped += 1
            continue

        markdown_content = md_path.read_text(encoding="utf-8")
        category = resource_id.split("/")[0]

        conn.execute(
            """INSERT INTO knowledge_resources
                   (id, category, keywords, priority, markdown_content, citation, last_updated)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   category=excluded.category,
                   keywords=excluded.keywords,
                   priority=excluded.priority,
                   markdown_content=excluded.markdown_content,
                   citation=excluded.citation,
                   last_updated=excluded.last_updated
            """,
            (
                resource_id,
                category,
                json.dumps(meta["keywords"]),
                meta["priority"],
                markdown_content,
                json.dumps(meta["citation"]),
                now,
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Seeded {inserted} knowledge resources ({skipped} skipped) into {db_path}")


if __name__ == "__main__":
    seed()
