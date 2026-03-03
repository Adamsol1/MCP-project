"""
Keyword registry for the Knowledge Bank.

Structure: each entry maps a logical name to its file path, a list of
trigger keywords (any one match is sufficient), a sort priority integer,
and an explicit category string.

Priority: 1 = geopolitical, 2 = sectors, 3 = threat_actors
"""

KNOWLEDGE_REGISTRY: dict[str, dict] = {
    # ── Geopolitical relationships ──────────────────────────────────────────
    "norway_russia": {
        "path": "knowledge_bank/geopolitical/norway_russia.md",
        "keywords": ["norway", "norwegian", "svalbard", "arctic", "russian"],
        "priority": 1,
        "category": "geopolitical",
    },
    "norway_china": {
        "path": "knowledge_bank/geopolitical/norway_china.md",
        "keywords": [
            "norway", "norwegian", "chinese", "huawei",
            "belt and road", "belt road", "bri", "new silk road", "obor",
        ],
        "priority": 1,
        "category": "geopolitical",
    },
    "eu_russia": {
        "path": "knowledge_bank/geopolitical/eu_russia.md",
        "keywords": ["european union", "eu", "russian", "gazprom", "nord stream"],
        "priority": 1,
        "category": "geopolitical",
    },
    "eu_usa": {
        "path": "knowledge_bank/geopolitical/eu_usa.md",
        "keywords": ["european union", "eu", "american", "transatlantic", "nato"],
        "priority": 1,
        "category": "geopolitical",
    },
    "eu_china": {
        "path": "knowledge_bank/geopolitical/eu_china.md",
        "keywords": [
            "european union", "eu", "chinese",
            "belt and road", "belt road", "bri", "new silk road", "obor",
        ],
        "priority": 1,
        "category": "geopolitical",
    },
    "usa_china": {
        "path": "knowledge_bank/geopolitical/usa_china.md",
        "keywords": [
            "american", "usa", "chinese", "taiwan", "trade war",
            "belt and road", "belt road", "bri", "new silk road", "obor",
        ],
        "priority": 1,
        "category": "geopolitical",
    },
    "usa_russia": {
        "path": "knowledge_bank/geopolitical/usa_russia.md",
        "keywords": ["american", "usa", "russian", "nato", "sanctions"],
        "priority": 1,
        "category": "geopolitical",
    },

    # ── Sectors ─────────────────────────────────────────────────────────────
    "energy": {
        "path": "knowledge_bank/sectors/energy.md",
        "keywords": ["energy", "oil", "gas", "pipeline", "lng"],
        "priority": 2,
        "category": "sectors",
    },
    "financial": {
        "path": "knowledge_bank/sectors/financial.md",
        "keywords": ["financial", "banking", "swift", "central bank"],
        "priority": 2,
        "category": "sectors",
    },
    "telecommunications": {
        "path": "knowledge_bank/sectors/telecommunications.md",
        "keywords": ["telecom", "5g", "telecommunications", "undersea cable"],
        "priority": 2,
        "category": "sectors",
    },

    # ── Threat actors ────────────────────────────────────────────────────────
    "russian_state": {
        "path": "knowledge_bank/threat_actors/russian_state.md",
        "keywords": ["apt28", "sandworm", "cozy bear", "fsb", "gru", "svr"],
        "priority": 3,
        "category": "threat_actors",
    },
    "chinese_state": {
        "path": "knowledge_bank/threat_actors/chinese_state.md",
        "keywords": ["apt41", "volt typhoon", "mss", "double dragon"],
        "priority": 3,
        "category": "threat_actors",
    },
}
