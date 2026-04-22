"""Seed knowledge.db with data from the MCP server's .md resource files.

Reads the KNOWLEDGE_REGISTRY from mcp_server/src/resources/__init__.py
(duplicated here to avoid import-path gymnastics) and each corresponding
.md file, then upserts every row into knowledge.db.

Usage:
    cd backend
    python scripts/seed_knowledge.py
"""

import json
import os
import random
import sqlite3
import sys
from datetime import datetime, date, UTC
from pathlib import Path

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_ROOT.parent
RESOURCES_DIR = PROJECT_ROOT / "generation_mcp_server" / "src" / "resources"
DATA_DIR = BACKEND_ROOT / "data"

_CREATED_AT_START = date(2010, 1, 1).toordinal()
_CREATED_AT_END = date(2025, 12, 31).toordinal()


def _random_created_at() -> str:
    ordinal = random.randint(_CREATED_AT_START, _CREATED_AT_END)
    d = date.fromordinal(ordinal)
    return datetime(d.year, d.month, d.day, tzinfo=UTC).isoformat()


KNOWLEDGE_REGISTRY: dict[str, dict] = {
    # ── Personas ──────────────────────────────────────────────────────────
    "personas/us": {"keywords": ["us", "united states", "american"], "priority": 0, "citation": None},
    "personas/norway": {"keywords": ["norway", "norwegian"], "priority": 0, "citation": None},
    "personas/china": {"keywords": ["china", "chinese"], "priority": 0, "citation": None},
    "personas/eu": {"keywords": ["eu", "european union"], "priority": 0, "citation": None},
    "personas/russia": {"keywords": ["russia", "russian"], "priority": 0, "citation": None},
    "personas/neutral": {"keywords": ["neutral"], "priority": 0, "citation": None},
    # ── Original geopolitical ──────────────────────────────────────────────
    "geopolitical/norway_russia": {
        "keywords": ["norway", "norwegian", "svalbard", "arctic", "russian", "russia"],
        "priority": 1,
        "citation": {
            "author": "Dr. Erik Haugen",
            "year": "2019",
            "title": "Norway–Russia Relations",
            "publisher": "Knowledge Base",
            "document_id": "KB-2019-041",
        },
    },
    "geopolitical/norway_china": {
        "keywords": [
            "norway", "norwegian", "chinese", "china", "huawei",
            "belt and road", "belt road", "bri", "new silk road", "obor",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Ingrid Larsson",
            "year": "2021",
            "title": "Norway–China Relations",
            "publisher": "Knowledge Base",
            "document_id": "KB-2021-029",
        },
    },
    "geopolitical/eu_russia": {
        "keywords": ["european union", "eu", "russian", "russia", "gazprom", "nord stream"],
        "priority": 1,
        "citation": {
            "author": "Dr. Sophie Brennan",
            "year": "2020",
            "title": "EU–Russia Relations",
            "publisher": "Knowledge Base",
            "document_id": "KB-2020-057",
        },
    },
    "geopolitical/eu_usa": {
        "keywords": ["european union", "eu", "american", "transatlantic", "nato"],
        "priority": 1,
        "citation": {
            "author": "James Thornton",
            "year": "2018",
            "title": "EU–United States Relations",
            "publisher": "Knowledge Base",
            "document_id": "KB-2018-023",
        },
    },
    "geopolitical/eu_china": {
        "keywords": [
            "european union", "eu", "chinese", "china",
            "belt and road", "belt road", "bri", "new silk road", "obor",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Mei Lin Chen",
            "year": "2022",
            "title": "EU–China Relations",
            "publisher": "Knowledge Base",
            "document_id": "KB-2022-006",
        },
    },
    "geopolitical/usa_china": {
        "keywords": [
            "american", "usa", "united states", "chinese", "china",
            "taiwan", "trade war", "belt and road", "belt road", "bri",
        ],
        "priority": 1,
        "citation": {
            "author": "Marcus Webb",
            "year": "2023",
            "title": "United States–China Relations",
            "publisher": "Knowledge Base",
            "document_id": "KB-2023-071",
        },
    },
    "geopolitical/usa_russia": {
        "keywords": [
            "american", "usa", "united states", "russian", "russia", "nato", "sanctions",
        ],
        "priority": 1,
        "citation": {
            "author": "Col. (ret.) David Richards",
            "year": "2022",
            "title": "United States–Russia Relations",
            "publisher": "Knowledge Base",
            "document_id": "KB-2022-032",
        },
    },
    # ── Nordic / Arctic ───────────────────────────────────────────────────
    "geopolitical/sweden_finland_nato": {
        "keywords": [
            "sweden", "swedish", "finland", "finnish", "nato", "nordic",
            "baltic", "accession", "membership",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Lars Eriksson",
            "year": "2024",
            "title": "Sweden and Finland NATO Accession",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-018",
        },
    },
    "geopolitical/arctic_sovereignty": {
        "keywords": [
            "arctic", "north pole", "polar", "svalbard", "northern sea route",
            "continental shelf", "icebreaker", "arctic council",
        ],
        "priority": 1,
        "citation": {
            "author": "Lt. Cmdr. (ret.) Thomas Berg",
            "year": "2023",
            "title": "Arctic Sovereignty and Militarization",
            "publisher": "Knowledge Base",
            "document_id": "KB-2023-024",
        },
    },
    "geopolitical/norway_nato": {
        "keywords": [
            "norway", "norwegian", "nato", "northern flank", "kola peninsula",
            "giuk gap", "andoya", "evenes", "marine corps prepositioning",
        ],
        "priority": 1,
        "citation": {
            "author": "Col. (ret.) Per Christensen",
            "year": "2024",
            "title": "Norway's Role in NATO",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-005",
        },
    },
    "geopolitical/nordic_china": {
        "keywords": [
            "nordic", "sweden", "norway", "denmark", "finland", "iceland",
            "huawei", "5g", "chinese", "china", "confucius",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Astrid Nilsson",
            "year": "2022",
            "title": "China's Presence and Influence in the Nordic Region",
            "publisher": "Knowledge Base",
            "document_id": "KB-2022-034",
        },
    },
    # ── Middle East & Gulf ────────────────────────────────────────────────
    "geopolitical/iran_usa": {
        "keywords": [
            "iran", "iranian", "jcpoa", "nuclear", "sanctions", "irgc",
            "houthi", "hezbollah", "proxy", "persian gulf",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Fatima Al-Rashid",
            "year": "2023",
            "title": "Iran–United States Relations",
            "publisher": "Knowledge Base",
            "document_id": "KB-2023-056",
        },
    },
    "geopolitical/iran_israel": {
        "keywords": [
            "iran", "iranian", "israel", "israeli", "mossad", "irgc",
            "shadow war", "hezbollah", "natanz", "drone", "missile",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Amara Osei",
            "year": "2024",
            "title": "Iran–Israel Shadow War",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-089",
        },
    },
    "geopolitical/gulf_states_china": {
        "keywords": [
            "saudi arabia", "saudi", "uae", "emirates", "gulf", "opec",
            "china", "chinese", "petrodollar", "yuan", "huawei", "5g",
        ],
        "priority": 1,
        "citation": {
            "author": "James Thornton",
            "year": "2024",
            "title": "Gulf States–China Relations",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-016",
        },
    },
    "geopolitical/middle_east_russia": {
        "keywords": [
            "russia", "russian", "syria", "libya", "wagner", "middle east",
            "tartus", "s-400", "arms sales", "iran drone",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Viktor Sokolov",
            "year": "2022",
            "title": "Russia's Strategic Presence in the Middle East",
            "publisher": "Knowledge Base",
            "document_id": "KB-2022-078",
        },
    },
    # ── Indo-Pacific ──────────────────────────────────────────────────────
    "geopolitical/china_taiwan": {
        "keywords": [
            "taiwan", "taiwanese", "pla", "strait", "amphibious", "tsmc",
            "semiconductor", "reunification", "a2ad", "strategic ambiguity",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Mei Lin Chen",
            "year": "2024",
            "title": "China–Taiwan: Taiwan Strait Scenario",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-009",
        },
    },
    "geopolitical/south_china_sea": {
        "keywords": [
            "south china sea", "nine-dash line", "spratly", "paracel",
            "philippines", "vietnam", "unclos", "artificial island", "fonop",
        ],
        "priority": 1,
        "citation": {
            "author": "Cmdr. (ret.) David Okafor",
            "year": "2023",
            "title": "South China Sea Territorial Disputes",
            "publisher": "Knowledge Base",
            "document_id": "KB-2023-067",
        },
    },
    "geopolitical/north_korea_capabilities": {
        "keywords": [
            "north korea", "dprk", "kim jong-un", "icbm", "nuclear",
            "lazarus", "hwasong", "missile", "cryptocurrency theft",
        ],
        "priority": 1,
        "citation": {
            "author": "Marcus Webb",
            "year": "2025",
            "title": "North Korea: Strategic Capabilities and Behaviour",
            "publisher": "Knowledge Base",
            "document_id": "KB-2025-004",
        },
    },
    "geopolitical/japan_south_korea_security": {
        "keywords": [
            "japan", "japanese", "south korea", "korean", "quad", "aukus",
            "senkaku", "thaad", "rearmament", "self-defence force",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Yuki Tanaka",
            "year": "2024",
            "title": "Japan and South Korea: Security Posture and Alliance Dynamics",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-074",
        },
    },
    # ── Sectors ────────────────────────────────────────────────────────────
    "sectors/energy": {
        "keywords": ["energy", "oil", "gas", "pipeline", "lng"],
        "priority": 2,
        "citation": {
            "author": "Dr. Astrid Nilsson",
            "year": "2016",
            "title": "Energy Sector Threat Landscape",
            "publisher": "Knowledge Base",
            "document_id": "KB-2016-009",
        },
    },
    "sectors/financial": {
        "keywords": ["financial", "banking", "swift", "central bank"],
        "priority": 2,
        "citation": {
            "author": "Nathan Ross",
            "year": "2020",
            "title": "Financial Sector Threat Landscape",
            "publisher": "Knowledge Base",
            "document_id": "KB-2020-063",
        },
    },
    "sectors/telecommunications": {
        "keywords": ["telecom", "5g", "telecommunications", "undersea cable"],
        "priority": 2,
        "citation": {
            "author": "Dr. Yuki Tanaka",
            "year": "2022",
            "title": "Telecommunications Sector Threat Landscape",
            "publisher": "Knowledge Base",
            "document_id": "KB-2022-048",
        },
    },
    "sectors/defense_industrial": {
        "keywords": [
            "defence", "defense", "industrial", "munitions", "weapons",
            "itar", "export control", "dual-use", "arms", "procurement",
        ],
        "priority": 2,
        "citation": {
            "author": "Col. (ret.) Richard Moore",
            "year": "2023",
            "title": "Defence Industrial Base: Threats and Vulnerabilities",
            "publisher": "Knowledge Base",
            "document_id": "KB-2023-044",
        },
    },
    "sectors/space": {
        "keywords": [
            "space", "satellite", "asat", "gps", "spoofing", "jamming",
            "starlink", "iss", "debris", "anti-satellite",
        ],
        "priority": 2,
        "citation": {
            "author": "Dr. Sarah Mitchell",
            "year": "2023",
            "title": "Space: Militarisation and Emerging Threats",
            "publisher": "Knowledge Base",
            "document_id": "KB-2023-082",
        },
    },
    "sectors/maritime": {
        "keywords": [
            "maritime", "shipping", "undersea cable", "ais", "spoofing",
            "shadow fleet", "houthi", "red sea", "port", "seabed",
        ],
        "priority": 2,
        "citation": {
            "author": "Lt. Cmdr. (ret.) Thomas Berg",
            "year": "2024",
            "title": "Maritime Security: Undersea Infrastructure and Gray-Zone Threats",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-013",
        },
    },
    "sectors/critical_infrastructure": {
        "keywords": [
            "critical infrastructure", "power grid", "water", "scada", "ics",
            "volt typhoon", "sandworm", "blackout", "sabotage",
        ],
        "priority": 2,
        "citation": {
            "author": "Nathan Ross",
            "year": "2024",
            "title": "Critical Infrastructure Threats",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-055",
        },
    },
    # ── Threat Actors ─────────────────────────────────────────────────────
    "threat_actors/russian_state": {
        "keywords": [
            "apt28", "sandworm", "cozy bear", "fancy bear", "turla",
            "fsb", "gru", "svr", "russia", "russian", "notpetya",
        ],
        "priority": 3,
        "citation": {
            "author": "Dr. Sophie Brennan",
            "year": "2024",
            "title": "Russian State-Sponsored Threat Actors",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-066",
        },
    },
    "threat_actors/chinese_state": {
        "keywords": [
            "apt41", "volt typhoon", "salt typhoon", "mss", "double dragon",
            "china", "chinese", "pla", "opm breach", "cloud hopper",
        ],
        "priority": 3,
        "citation": {
            "author": "Dr. Mei Lin Chen",
            "year": "2025",
            "title": "Chinese State-Sponsored Threat Actors",
            "publisher": "Knowledge Base",
            "document_id": "KB-2025-022",
        },
    },
    # ── Behaviors ─────────────────────────────────────────────────────────
    "behaviors/russia_hybrid": {
        "keywords": [
            "hybrid warfare", "disinformation", "russia", "russian",
            "sabotage", "election interference", "energy weaponisation",
            "ira", "internet research agency", "influence operation",
        ],
        "priority": 2,
        "citation": {
            "author": "Dr. Sophie Brennan",
            "year": "2024",
            "title": "Russia: Hybrid Warfare Doctrine and Behavioural Patterns",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-031",
        },
    },
    "behaviors/china_influence": {
        "keywords": [
            "united front", "ufwd", "confucius institute", "china", "chinese",
            "ip theft", "talent recruitment", "thousand talents", "supply chain",
        ],
        "priority": 2,
        "citation": {
            "author": "Dr. Mei Lin Chen",
            "year": "2023",
            "title": "China: Influence Operations and Espionage Patterns",
            "publisher": "Knowledge Base",
            "document_id": "KB-2023-077",
        },
    },
    "behaviors/iran_cyber": {
        "keywords": [
            "iran", "iranian", "apt33", "apt34", "oilrig", "charming kitten",
            "shamoon", "wiper", "irgc", "mois", "ics attack",
        ],
        "priority": 2,
        "citation": {
            "author": "Dr. Fatima Al-Rashid",
            "year": "2024",
            "title": "Iran: Cyber Operations and Behaviour Patterns",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-022",
        },
    },
    "behaviors/north_korea_financial": {
        "keywords": [
            "north korea", "dprk", "lazarus", "apt38", "cryptocurrency",
            "crypto theft", "swift", "sanctions evasion", "money laundering",
        ],
        "priority": 2,
        "citation": {
            "author": "Nathan Ross",
            "year": "2025",
            "title": "North Korea: Financial Operations and Sanctions Evasion",
            "publisher": "Knowledge Base",
            "document_id": "KB-2025-011",
        },
    },
    # ── Conflicts ──────────────────────────────────────────────────────────
    "conflicts/ukraine_russia_war": {
        "keywords": [
            "ukraine", "ukrainian", "russia", "russian", "war", "invasion",
            "himars", "drone", "artillery", "donbas", "kursk",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Viktor Sokolov",
            "year": "2025",
            "title": "Russia–Ukraine War (2022–present)",
            "publisher": "Knowledge Base",
            "document_id": "KB-2025-039",
        },
    },
    "conflicts/israel_hamas_2023": {
        "keywords": [
            "israel", "israeli", "hamas", "gaza", "october 7",
            "hezbollah", "houthi", "idf", "red sea", "iran",
        ],
        "priority": 1,
        "citation": {
            "author": "Dr. Amara Osei",
            "year": "2024",
            "title": "Israel–Hamas War (2023–present)",
            "publisher": "Knowledge Base",
            "document_id": "KB-2024-097",
        },
    },
}


def seed() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_path = Path(os.getenv("KNOWLEDGE_DB_PATH", str(DATA_DIR / "knowledge.db")))
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_resources (
            id              TEXT PRIMARY KEY,
            category        TEXT NOT NULL DEFAULT '',
            keywords        TEXT NOT NULL DEFAULT '[]',
            priority        INTEGER NOT NULL DEFAULT 1,
            markdown_content TEXT NOT NULL DEFAULT '',
            citation        TEXT,
            created_at      DATETIME,
            last_updated    DATETIME NOT NULL
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
        created_at = _random_created_at()

        conn.execute(
            """INSERT INTO knowledge_resources
                   (id, category, keywords, priority, markdown_content, citation, created_at, last_updated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   category=excluded.category,
                   keywords=excluded.keywords,
                   priority=excluded.priority,
                   markdown_content=excluded.markdown_content,
                   citation=excluded.citation,
                   created_at=COALESCE(knowledge_resources.created_at, excluded.created_at),
                   last_updated=excluded.last_updated
            """,
            (
                resource_id,
                category,
                json.dumps(meta["keywords"]),
                meta["priority"],
                markdown_content,
                json.dumps(meta["citation"]),
                created_at,
                now,
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Seeded {inserted} knowledge resources ({skipped} skipped) into {db_path}")


if __name__ == "__main__":
    seed()
