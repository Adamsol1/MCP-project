"""Seed perspective_documents table with official government reference documents.

Each perspective (us, norway, eu, china, russia) gets three documents covering
Political, Economic, and Military sections. Content represents key positions and
doctrines that a threat analyst would reference when interpreting state behaviour.

Two sources are combined:
  1. PERSPECTIVE_DOCUMENTS list below — hand-authored baseline entries.
  2. perspective_docs/ directory — one Markdown file per document with YAML
     frontmatter containing metadata (id, perspective, section, title, source,
     date_published). Files in this directory override list entries with the same id.

Usage:
    cd backend
    python scripts/seed_perspective_docs.py
"""

import os
import re
import sqlite3
from datetime import datetime, UTC
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
DATA_DIR = BACKEND_ROOT / "data"

PERSPECTIVE_DOCUMENTS: list[dict] = [
    # ── RUSSIA ───────────────────────────────────────────────────────────────
    {
        "id": "russia_foreign_policy_concept_2023",
        "perspective": "russia",
        "section": "political",
        "title": "Russian Foreign Policy Concept 2023",
        "source": "Russian Federation Presidential Decree No. 229, March 2023",
        "date_published": datetime(2023, 3, 31, tzinfo=UTC),
        "markdown_content": """# Russian Foreign Policy Concept 2023

## Strategic Framework
The 2023 Foreign Policy Concept is the most explicit articulation of Russian ideology since the Soviet collapse. It frames Russia as a "civilisational state" leading the "Russian world" (Russkiy Mir) and positions the West — particularly the US and its "satellites" — as existential adversaries pursuing Russia's "weakening, division and destruction."

## Anti-Western Framing
The concept explicitly identifies the US as seeking to "preserve global hegemony" through "divide and rule" tactics. NATO is characterised as a destabilising force that drew closer to Russian borders in violation of alleged (unwritten) commitments. The EU is seen as a tool of American strategy rather than an independent actor.

## Sovereign Democracy
Russia's preferred international order is "multi-polar" — replacing US-led unipolarity with a system in which Russia, China, and "the Global South" constitute co-equal poles. Russia frames its opposition to Western-backed democracy promotion as defence of sovereignty and non-interference.

## "Russian World" and Near Abroad
The concept asserts Russia's right to protect "Russian-speaking populations" abroad — the legal and ideological basis for interventions in Ukraine (2014, 2022), Georgia (2008), and Moldova. This doctrine provides justification for destabilisation operations against any post-Soviet state deemed to be "drifting" toward the West.

## China Partnership
Russia-China relations are described as a "comprehensive strategic partnership" with "no limits" — not a military alliance but a convergence of interests in opposing US dominance. Russia frames this as a cornerstone of the emerging multi-polar order.

## Intelligence Implications
The 2023 concept provides the ideological framework for Russian intelligence operations: undermining NATO solidarity, supporting anti-Western political movements in Europe, destabilising post-Soviet states, and cultivating "Global South" opposition to Western sanctions.
""",
    },
    {
        "id": "russia_economic_warfare_doctrine",
        "perspective": "russia",
        "section": "economic",
        "title": "Russian Economic Coercion and Sanctions Circumvention",
        "source": "Assessment based on Russian Central Bank, Finance Ministry, and open-source analysis, 2022-2024",
        "date_published": datetime(2023, 9, 14, tzinfo=UTC),
        "markdown_content": """# Russian Economic Coercion and Sanctions Circumvention

## Weaponisation of Energy Supply
Prior to the 2022 invasion, Russia supplied ~40% of EU natural gas and ~25% of EU oil. Russia demonstrated willingness to manipulate energy supply as geopolitical leverage through: the 2006 and 2009 Ukraine gas crises, gradual Nord Stream gas reductions in 2021-2022 preceding the invasion, and complete cutoff of supply to most EU members by late 2022. This strategy ultimately failed — EU diversification accelerated and dependency was reduced.

## Sanctions Adaptation and Circumvention
In response to unprecedented Western sanctions (asset freezes, SWIFT exclusions, export controls), Russia has implemented:
- **Parallel import schemes**: Importing sanctioned goods through Kazakhstan, Armenia, Turkey, UAE, and China as intermediaries
- **Yuan/Rupee trade settlement**: Redirecting trade to non-dollar currencies and non-Western payment systems (MIR, CIPS)
- **Shadow fleet expansion**: Operating 600+ vessels outside Western-insured shipping lanes to export oil above the price cap
- **Domestic substitution**: Accelerated import replacement (with mixed results; semiconductor-dependent industries have suffered)

## War Economy Shift
Russia has pivoted to a war economy: defence spending reached 6% of GDP in 2024 (vs. 3.9% pre-war), industrial production capacity is being redirected to military outputs, and labour market controls are preventing mass flight of skilled workers.

## Financial Vulnerability
Frozen Russian state assets (~$300 billion held in Western central banks, primarily Euroclear in Belgium) represent both a Russian vulnerability and a legal challenge for Western governments seeking to use these funds for Ukraine reconstruction.

## Intelligence Implications
Russia's economic adaptation has been more successful than Western planners anticipated. Sanctions have imposed significant costs but have not collapsed the Russian economy. The circumvention network — particularly through Central Asian and Caucasian intermediaries — supplies dual-use components for weapons production.
""",
    },
    {
        "id": "russia_military_doctrine_posture",
        "perspective": "russia",
        "section": "military",
        "title": "Russian Military Doctrine and Operational Posture",
        "source": "Russian Security Council / General Staff, 2014-2023",
        "date_published": datetime(2022, 11, 2, tzinfo=UTC),
        "markdown_content": """# Russian Military Doctrine and Operational Posture

## Doctrine Overview
Russian military doctrine (2014, updated 2022) frames NATO and the US as existential threats and authorises nuclear use in conventional conflict scenarios where "the very existence of the state is under threat." This deliberately ambiguous threshold is a calculated escalation management tool — designed to deter NATO intervention in Russian conflicts with non-NATO states.

## Nuclear Signalling and Escalation Management
Russia's nuclear signalling during the Ukraine war — deploying tactical nuclear weapons to Belarus (2023), periodic references to nuclear use thresholds — is deliberate and serves three purposes:
1. Deterring NATO direct intervention in Ukraine
2. Slowing or stopping Western weapons deliveries to Ukraine
3. Demonstrating resolve to domestic and international audiences

Russia maintains approximately 1,900 deployed strategic warheads and 2,000+ tactical nuclear weapons (non-strategic), the world's largest tactical nuclear arsenal.

## New Generation Warfare
The Gerasimov-attributed "new generation warfare" concept (not actually a formal Gerasimov doctrine, but a Western analytical frame) describes Russian approach: coordinated use of political subversion, cyber operations, information operations, and conventional military forces. The 2022 invasion demonstrated both the ambitions and limits of this approach.

## Lessons from Ukraine
The Ukraine war has exposed significant Russian military weaknesses: C2 failures, logistics bottlenecks, leadership casualties (battalion and brigade commanders killed at unprecedented rates), and insufficient combined-arms integration. Russia has adapted: increased use of FPV drones, electronic warfare, and depth in defensive lines. Force regeneration through conscription and mobilisation has restored numerical strength at reduced quality.

## Northern Fleet and Arctic Posture
The Northern Fleet (elevated to Military District status in 2021) is Russia's premier force projection asset. Ballistic missile submarines (SSBNs) based on the Kola Peninsula carry the majority of Russia's second-strike capability. The Northern Fleet's conventional forces provide Arctic military dominance and coastal defence.

## Intelligence Implications
Russia's demonstrated willingness to use nuclear signalling as a coercive tool — and the West's partial response (constraining some weapons transfers) — has reinforced Russian confidence in escalation management. Russian conventional military performance in Ukraine provides actionable data on capability gaps that NATO planners and adversary intelligence services are exploiting.
""",
    },
]


DOCS_DIR = SCRIPT_DIR / "perspective_docs"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from markdown body. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.index("---", 3)
    fm_block = text[3:end].strip()
    body = text[end + 3:].strip()
    meta: dict = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip().strip('"')
    return meta, body


def _load_markdown_docs() -> list[dict]:
    """Load all .md files from perspective_docs/ as seed entries."""
    docs = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        if not meta.get("id"):
            continue
        raw_date = meta.get("date_published", "2000-01-01")
        parts = [int(p) for p in raw_date.split("-")]
        date_published = datetime(*parts, tzinfo=UTC)
        docs.append({
            "id": meta["id"],
            "perspective": meta["perspective"],
            "section": meta["section"],
            "title": meta["title"],
            "source": meta.get("source", ""),
            "date_published": date_published,
            "markdown_content": body,
        })
    return docs


def seed() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_path = Path(os.getenv("KNOWLEDGE_DB_PATH", str(DATA_DIR / "knowledge.db")))
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS perspective_documents (
            id               TEXT PRIMARY KEY,
            perspective      TEXT NOT NULL,
            section          TEXT NOT NULL,
            title            TEXT NOT NULL,
            source           TEXT,
            date_published   DATETIME NOT NULL,
            markdown_content TEXT NOT NULL DEFAULT '',
            is_active        INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persp_docs_perspective ON perspective_documents(perspective)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persp_docs_section ON perspective_documents(section)")

    # Merge: file-based docs override list entries with the same id
    file_docs = _load_markdown_docs()
    file_ids = {d["id"] for d in file_docs}
    all_docs = [d for d in PERSPECTIVE_DOCUMENTS if d["id"] not in file_ids] + file_docs

    inserted = 0
    for doc in all_docs:
        conn.execute(
            """INSERT INTO perspective_documents
                   (id, perspective, section, title, source, date_published, markdown_content, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)
               ON CONFLICT(id) DO UPDATE SET
                   perspective=excluded.perspective,
                   section=excluded.section,
                   title=excluded.title,
                   source=excluded.source,
                   date_published=excluded.date_published,
                   markdown_content=excluded.markdown_content
            """,
            (
                doc["id"],
                doc["perspective"],
                doc["section"],
                doc["title"],
                doc.get("source"),
                doc["date_published"].isoformat(),
                doc["markdown_content"],
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Seeded {inserted} perspective documents into {db_path}")
    print(f"  {len(file_docs)} from perspective_docs/ markdown files")
    print(f"  {inserted - len(file_docs)} from inline PERSPECTIVE_DOCUMENTS list")


if __name__ == "__main__":
    seed()
