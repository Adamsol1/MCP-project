import pytest

from knowledge_bank.service import KnowledgeService

# ── Shared fixture ──────────────────────────────────────────────────────────

@pytest.fixture
def registry():
    """
    Representative subset of the real registry:
    3 geo + 3 sectors + 2 threat_actors = 8 entries.
    Large enough to exercise all trimming and ordering scenarios with a cap of 5.

    Matching contract: ANY keyword in an entry's list triggers that entry (OR logic).
    Multi-word keywords (e.g. 'belt and road') must appear as an exact phrase.
    """
    return {
        "norway_russia": {
            "path": "knowledge_bank/geopolitical/norway_russia.md",
            "keywords": ["norway", "norwegian", "svalbard", "arctic", "russian"],
            "priority": 1,
            "category": "geopolitical",
        },
        "eu_china": {
            "path": "knowledge_bank/geopolitical/eu_china.md",
            "keywords": ["european union", "eu", "chinese", "belt and road", "bri"],
            "priority": 1,
            "category": "geopolitical",
        },
        "usa_russia": {
            "path": "knowledge_bank/geopolitical/usa_russia.md",
            "keywords": ["american", "usa", "russian", "nato", "sanctions"],
            "priority": 1,
            "category": "geopolitical",
        },
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


# ── Group 1: Basic construction ─────────────────────────────────────────────

def test_service_accepts_registry(registry):
    """KnowledgeService must be constructible with the nested registry dict."""
    service = KnowledgeService(registry)
    assert service is not None


# ── Group 2: Edge cases ─────────────────────────────────────────────────────

def test_empty_text_returns_empty_list(registry):
    """No text → no matches. Guards against crashes on empty input."""
    service = KnowledgeService(registry)
    assert service.get_relevant_resources("") == []


def test_no_matching_keywords_returns_empty_list(registry):
    """Text with no known keywords → empty list."""
    service = KnowledgeService(registry)
    result = service.get_relevant_resources("The weather in Paris is lovely.")
    assert result == []


# ── Group 3: Matching behaviour ─────────────────────────────────────────────

def test_any_single_keyword_triggers_entry(registry):
    """
    OR logic: ONE keyword from an entry's list is sufficient to match it.
    Only 'arctic' appears — none of the other norway_russia keywords do.
    """
    service = KnowledgeService(registry)
    result = service.get_relevant_resources(
        "The Arctic is increasingly contested territory."
    )
    assert "knowledge_bank/geopolitical/norway_russia.md" in result


def test_multiple_keywords_same_entry_deduplicates(registry):
    """
    Several keywords from the same entry match → the path appears only once.
    'norway' and 'svalbard' are both in norway_russia's keyword list.
    """
    service = KnowledgeService(registry)
    result = service.get_relevant_resources(
        "Norway's Svalbard archipelago faces Russian pressure."
    )
    assert result.count("knowledge_bank/geopolitical/norway_russia.md") == 1


def test_keyword_matching_is_case_insensitive(registry):
    """Matching must be case-insensitive: 'ARCTIC', 'Arctic', 'arctic' all trigger."""
    service = KnowledgeService(registry)
    upper = service.get_relevant_resources("ARCTIC shipping lanes are now disputed.")
    title = service.get_relevant_resources("Arctic shipping lanes are now disputed.")
    lower = service.get_relevant_resources("arctic shipping lanes are now disputed.")
    assert upper == title == lower


def test_phrase_keyword_matches_when_exact_phrase_present(registry):
    """
    Multi-word keywords must match when the exact phrase appears in the text.
    'belt and road' should trigger eu_china.
    """
    service = KnowledgeService(registry)
    result = service.get_relevant_resources(
        "The Belt and Road Initiative is expanding into Eastern Europe."
    )
    assert "knowledge_bank/geopolitical/eu_china.md" in result


def test_phrase_keyword_does_not_match_on_partial_phrase(registry):
    """
    'belt and road' must NOT match text that only contains 'belt' in isolation.
    Guards against false positives from substring overlap.
    """
    service = KnowledgeService(registry)
    result = service.get_relevant_resources(
        "The conveyor belt system was upgraded in the factory."
    )
    assert "knowledge_bank/geopolitical/eu_china.md" not in result


# ── Group 4: Result limits ──────────────────────────────────────────────────

def test_returns_at_most_5_results(registry):
    """Even when 6+ entries match, the result list is capped at 5."""
    service = KnowledgeService(registry)
    # Triggers all 3 geo + all 3 sectors = 6 distinct entries
    result = service.get_relevant_resources(
        "Norway faced Russian pressure while EU-China tensions and USA-Russian "
        "sanctions impacted energy, financial services, and telecommunications."
    )
    assert len(result) <= 5


# ── Group 5: Priority ordering ──────────────────────────────────────────────

def test_geopolitical_beats_sectors_when_trimming(registry):
    """
    When matches exceed 5, geopolitical paths survive over sectors.
    Triggers: all 3 geo + all 3 sectors = 6 matches → trimmed to 5
    → all 3 geo paths must be kept, one sector is dropped.
    """
    service = KnowledgeService(registry)
    result = service.get_relevant_resources(
        "Norway faced Russian pressure while EU-China tensions and USA-Russian "
        "sanctions impacted energy, financial services, and telecommunications."
    )
    assert "knowledge_bank/geopolitical/norway_russia.md" in result
    assert "knowledge_bank/geopolitical/eu_china.md" in result
    assert "knowledge_bank/geopolitical/usa_russia.md" in result
    assert len(result) == 5


def test_sectors_beats_threat_actors_when_trimming(registry):
    """
    When matches exceed 5, sector paths survive over threat_actors.
    Triggers: 1 geo + all 3 sectors + 2 threats = 6 matches → trimmed to 5
    → all 3 sector paths must be kept, one threat actor is dropped.
    """
    service = KnowledgeService(registry)
    result = service.get_relevant_resources(
        "Norway's energy sector, financial systems, and telecommunications "
        "infrastructure were targeted by APT28 and MSS operatives."
    )
    assert "knowledge_bank/sectors/energy.md" in result
    assert "knowledge_bank/sectors/financial.md" in result
    assert "knowledge_bank/sectors/telecommunications.md" in result
    assert len(result) == 5


def test_results_are_returned_in_priority_order(registry):
    """
    Returned list must be ordered: geopolitical first, then sectors,
    then threat_actors. Triggers exactly 3 matches — one per category,
    cap not hit.
    """
    service = KnowledgeService(registry)
    result = service.get_relevant_resources(
        "Norway's Arctic energy sector was compromised by APT28."
    )
    assert result[0] == "knowledge_bank/geopolitical/norway_russia.md"
    assert result[1] == "knowledge_bank/sectors/energy.md"
    assert result[2] == "knowledge_bank/threat_actors/russian_state.md"
