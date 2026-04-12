"""TDD tests for the Collection Coverage Confidence Score algorithm.

Written before implementation. Tests verify the scoring logic described in the plan:
- Coverage dimension (0.45 weight)
- Source diversity dimension (0.35 weight)
- Gap penalty dimension (0.20 weight)
- Tier boundaries
- Priority-weighted aggregate
"""

import pytest

from src.models.analysis import FindingModel, ProcessingResult
from src.models.confidence import CollectionCoverageResult, ConfidenceTier
from src.services.confidence.collection_coverage import compute_collection_coverage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    id: str,
    source: str,
    relevant_to: list[str],
    confidence: int = 70,
) -> FindingModel:
    return FindingModel(
        id=id,
        title=f"Finding {id}",
        finding=f"Finding body {id}",
        evidence_summary="Evidence.",
        source=source,
        confidence=confidence,
        relevant_to=relevant_to,
        supporting_data={},
        why_it_matters="Matters.",
        uncertainties=[],
    )


def _pir(question: str, priority: str = "high", rationale: str = "Important.") -> dict:
    return {"question": question, "priority": priority, "rationale": rationale}


# ---------------------------------------------------------------------------
# Per-PIR edge cases
# ---------------------------------------------------------------------------


class TestZeroFindings:
    """Zero findings for a high-priority PIR → LOW tier, score near 0."""

    def test_tier_is_low(self):
        pirs = [_pir("What are the indicators of an imminent attack?", priority="high")]
        result = compute_collection_coverage(findings=[], gaps=[], pirs=pirs)
        assert result.per_pir[0].tier == ConfidenceTier.LOW

    def test_score_near_zero(self):
        pirs = [_pir("What are the indicators of an imminent attack?", priority="high")]
        result = compute_collection_coverage(findings=[], gaps=[], pirs=pirs)
        # With 0 coverage and 0 diversity, only gap_penalty (no gaps) contributes
        # score = 0*0.45 + 0*0.35 + 1.0*0.20 = 0.20
        assert result.per_pir[0].score == pytest.approx(0.20, abs=0.01)

    def test_finding_count_is_zero(self):
        pirs = [_pir("What are the indicators?")]
        result = compute_collection_coverage(findings=[], gaps=[], pirs=pirs)
        assert result.per_pir[0].finding_count == 0

    def test_high_priority_warning_in_rationale(self):
        pirs = [_pir("What are indicators?", priority="high")]
        result = compute_collection_coverage(findings=[], gaps=[], pirs=pirs)
        assert "HIGH-PRIORITY" in result.per_pir[0].rationale


class TestOneFindings:
    """One finding from one source → LOW or MODERATE."""

    def test_score_is_correct(self):
        # coverage=0.50 * 0.45 + diversity=0.30 * 0.35 + gap_penalty=1.0 * 0.20
        # = 0.225 + 0.105 + 0.20 = 0.530
        pirs = [_pir("What are the cyber indicators?")]
        findings = [_make_finding("f1", "otx", ["PIR-0"])]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert result.per_pir[0].score == pytest.approx(0.530, abs=0.01)

    def test_tier_is_moderate(self):
        pirs = [_pir("What are the cyber indicators?")]
        findings = [_make_finding("f1", "otx", ["PIR-0"])]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert result.per_pir[0].tier == ConfidenceTier.MODERATE

    def test_finding_count_is_one(self):
        pirs = [_pir("What are the cyber indicators?")]
        findings = [_make_finding("f1", "otx", ["PIR-0"])]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert result.per_pir[0].finding_count == 1

    def test_source_types_has_one_entry(self):
        pirs = [_pir("What are the cyber indicators?")]
        findings = [_make_finding("f1", "otx", ["PIR-0"])]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert len(result.per_pir[0].source_types) == 1


class TestThreeFindingsThreeSources:
    """3 findings from 3 source types, no gaps → HIGH or ASSESSED."""

    def test_score_is_high(self):
        # coverage=1.0*0.45 + diversity=0.90*0.35 + gap_penalty=1.0*0.20
        # = 0.45 + 0.315 + 0.20 = 0.965
        pirs = [_pir("How would cyber capabilities be deployed?")]
        findings = [
            _make_finding("f1", "otx", ["PIR-0"]),
            _make_finding("f2", "web_search", ["PIR-0"]),
            _make_finding("f3", "knowledge_bank", ["PIR-0"]),
        ]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert result.per_pir[0].score == pytest.approx(0.965, abs=0.01)

    def test_tier_is_assessed(self):
        pirs = [_pir("How would cyber capabilities be deployed?")]
        findings = [
            _make_finding("f1", "otx", ["PIR-0"]),
            _make_finding("f2", "web_search", ["PIR-0"]),
            _make_finding("f3", "knowledge_bank", ["PIR-0"]),
        ]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert result.per_pir[0].tier == ConfidenceTier.ASSESSED

    def test_no_gap_flag(self):
        pirs = [_pir("How would cyber capabilities be deployed?")]
        findings = [
            _make_finding("f1", "otx", ["PIR-0"]),
            _make_finding("f2", "web_search", ["PIR-0"]),
            _make_finding("f3", "knowledge_bank", ["PIR-0"]),
        ]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert result.per_pir[0].has_gap_flag is False


class TestGapPenalty:
    """Gap string mentioning PIR topic reduces score."""

    def test_gap_flag_is_set(self):
        pirs = [_pir("What economic sanctions would be imposed?")]
        findings = [_make_finding("f1", "otx", ["PIR-0"])]
        gaps = ["No data on economic sanctions countermeasures"]
        result = compute_collection_coverage(findings=findings, gaps=gaps, pirs=pirs)
        assert result.per_pir[0].has_gap_flag is True

    def test_score_drops_with_gap(self):
        pirs = [_pir("What economic sanctions would be imposed?")]
        findings = [_make_finding("f1", "otx", ["PIR-0"])]
        gaps = ["No data on economic sanctions countermeasures"]

        result_no_gap = compute_collection_coverage(
            findings=findings, gaps=[], pirs=pirs
        )
        result_with_gap = compute_collection_coverage(
            findings=findings, gaps=gaps, pirs=pirs
        )
        assert result_with_gap.per_pir[0].score < result_no_gap.per_pir[0].score

    def test_gap_penalty_value(self):
        # With gap: coverage=0.50*0.45 + diversity=0.30*0.35 + gap_penalty=0.20*0.20
        # = 0.225 + 0.105 + 0.04 = 0.370
        pirs = [_pir("What economic sanctions would be imposed?")]
        findings = [_make_finding("f1", "otx", ["PIR-0"])]
        gaps = ["sanctions data is missing"]
        result = compute_collection_coverage(findings=findings, gaps=gaps, pirs=pirs)
        assert result.per_pir[0].score == pytest.approx(0.370, abs=0.01)


class TestAggregateWeighting:
    """Aggregate weighted by priority: high PIR (LOW) + low PIR (HIGH) → pulled toward LOW."""

    def test_aggregate_pulled_by_high_priority(self):
        pirs = [
            _pir("High priority PIR with no data", priority="high"),
            _pir("Low priority PIR with full data", priority="low"),
        ]
        findings = [
            _make_finding("f1", "otx", ["PIR-1"]),
            _make_finding("f2", "web_search", ["PIR-1"]),
            _make_finding("f3", "knowledge_bank", ["PIR-1"]),
        ]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        pir0 = result.per_pir[0]
        pir1 = result.per_pir[1]
        assert pir0.tier == ConfidenceTier.LOW
        assert pir1.tier in (ConfidenceTier.HIGH, ConfidenceTier.ASSESSED)
        # aggregate should be closer to LOW than ASSESSED
        assert result.aggregate_score < pir1.score

    def test_aggregate_tier_is_not_assessed(self):
        pirs = [
            _pir("High priority PIR with no data", priority="high"),
            _pir("Low priority PIR with full data", priority="low"),
        ]
        findings = [
            _make_finding("f1", "otx", ["PIR-1"]),
            _make_finding("f2", "web_search", ["PIR-1"]),
            _make_finding("f3", "knowledge_bank", ["PIR-1"]),
        ]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert result.aggregate_tier != ConfidenceTier.ASSESSED


class TestEmptyFindings:
    """Empty findings list → all PIRs are LOW."""

    def test_all_pirs_low(self):
        pirs = [
            _pir("PIR one", priority="high"),
            _pir("PIR two", priority="medium"),
            _pir("PIR three", priority="low"),
        ]
        result = compute_collection_coverage(findings=[], gaps=[], pirs=pirs)
        for pir_score in result.per_pir:
            assert pir_score.tier == ConfidenceTier.LOW

    def test_returns_correct_pir_count(self):
        pirs = [_pir("A"), _pir("B"), _pir("C")]
        result = compute_collection_coverage(findings=[], gaps=[], pirs=pirs)
        assert len(result.per_pir) == 3


class TestUnmatchedFindings:
    """Findings with relevant_to not matching any PIR → ignored, no crash."""

    def test_no_crash_on_unmatched(self):
        pirs = [_pir("PIR about malware")]
        findings = [_make_finding("f1", "otx", ["PIR-99"])]  # PIR-99 doesn't exist
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert result.per_pir[0].finding_count == 0

    def test_pir_score_unchanged_by_unmatched(self):
        pirs = [_pir("PIR about malware")]
        findings_unmatched = [_make_finding("f1", "otx", ["PIR-99"])]
        result_unmatched = compute_collection_coverage(
            findings=findings_unmatched, gaps=[], pirs=pirs
        )
        result_empty = compute_collection_coverage(findings=[], gaps=[], pirs=pirs)
        assert result_unmatched.per_pir[0].score == pytest.approx(
            result_empty.per_pir[0].score, abs=0.01
        )


class TestTierBoundaries:
    """Boundary tests: score exactly at tier thresholds maps to correct tier."""

    def _score_to_tier(self, score: float) -> ConfidenceTier:
        """Helper: create a scenario that produces approx the given score."""
        # We verify through the actual function using a known setup, not internal mapping.
        # Use: coverage=score/0.45 trick won't work cleanly, so test the mapping separately.
        from src.services.confidence.collection_coverage import _score_to_tier as _map
        return _map(score)

    def test_score_039_is_low(self):
        from src.services.confidence.collection_coverage import _score_to_tier
        assert _score_to_tier(0.39) == ConfidenceTier.LOW

    def test_score_040_is_moderate(self):
        from src.services.confidence.collection_coverage import _score_to_tier
        assert _score_to_tier(0.40) == ConfidenceTier.MODERATE

    def test_score_069_is_moderate(self):
        from src.services.confidence.collection_coverage import _score_to_tier
        assert _score_to_tier(0.69) == ConfidenceTier.MODERATE

    def test_score_070_is_high(self):
        from src.services.confidence.collection_coverage import _score_to_tier
        assert _score_to_tier(0.70) == ConfidenceTier.HIGH

    def test_score_089_is_high(self):
        from src.services.confidence.collection_coverage import _score_to_tier
        assert _score_to_tier(0.89) == ConfidenceTier.HIGH

    def test_score_090_is_assessed(self):
        from src.services.confidence.collection_coverage import _score_to_tier
        assert _score_to_tier(0.90) == ConfidenceTier.ASSESSED

    def test_score_100_is_assessed(self):
        from src.services.confidence.collection_coverage import _score_to_tier
        assert _score_to_tier(1.00) == ConfidenceTier.ASSESSED

    def test_score_000_is_low(self):
        from src.services.confidence.collection_coverage import _score_to_tier
        assert _score_to_tier(0.00) == ConfidenceTier.LOW


class TestSourceTypeNormalization:
    """Source types are normalized to canonical categories."""

    def test_osint_maps_to_otx(self):
        pirs = [_pir("PIR about infrastructure")]
        findings = [
            _make_finding("f1", "osint", ["PIR-0"]),
            _make_finding("f2", "otx", ["PIR-0"]),
        ]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        # Both normalize to "otx" → 1 source type
        assert len(result.per_pir[0].source_types) == 1

    def test_knowledge_base_maps_to_knowledge_bank(self):
        pirs = [_pir("PIR about actors")]
        findings = [
            _make_finding("f1", "knowledge_base", ["PIR-0"]),
            _make_finding("f2", "knowledge_bank", ["PIR-0"]),
        ]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert len(result.per_pir[0].source_types) == 1

    def test_unknown_source_maps_to_other(self):
        pirs = [_pir("PIR")]
        findings = [_make_finding("f1", "some_unknown_source", ["PIR-0"])]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert "other" in result.per_pir[0].source_types


class TestEmptyPirs:
    """Empty PIR list returns a valid result with empty per_pir."""

    def test_empty_pirs_returns_valid_result(self):
        result = compute_collection_coverage(findings=[], gaps=[], pirs=[])
        assert isinstance(result, CollectionCoverageResult)
        assert result.per_pir == []

    def test_empty_pirs_aggregate_score_is_zero(self):
        result = compute_collection_coverage(findings=[], gaps=[], pirs=[])
        assert result.aggregate_score == pytest.approx(0.0)

    def test_empty_pirs_aggregate_tier_is_low(self):
        result = compute_collection_coverage(findings=[], gaps=[], pirs=[])
        assert result.aggregate_tier == ConfidenceTier.LOW


class TestAggregateSummary:
    """Aggregate summary is a non-empty string."""

    def test_summary_is_non_empty(self):
        pirs = [_pir("What are the key indicators?")]
        result = compute_collection_coverage(findings=[], gaps=[], pirs=pirs)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0


class TestTwoFindingsSameSource:
    """Two findings from same source type → coverage 0.75, diversity 0.30."""

    def test_score(self):
        # coverage=0.75*0.45 + diversity=0.30*0.35 + gap=1.0*0.20
        # = 0.3375 + 0.105 + 0.20 = 0.6425
        pirs = [_pir("PIR")]
        findings = [
            _make_finding("f1", "otx", ["PIR-0"]),
            _make_finding("f2", "otx", ["PIR-0"]),
        ]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert result.per_pir[0].score == pytest.approx(0.6425, abs=0.01)
        assert result.per_pir[0].tier == ConfidenceTier.MODERATE


class TestFourSourceTypes:
    """Four distinct source types → diversity score 1.0."""

    def test_four_source_diversity(self):
        # coverage=1.0*0.45 + diversity=1.0*0.35 + gap=1.0*0.20 = 1.0
        pirs = [_pir("PIR")]
        findings = [
            _make_finding("f1", "otx", ["PIR-0"]),
            _make_finding("f2", "web_search", ["PIR-0"]),
            _make_finding("f3", "knowledge_bank", ["PIR-0"]),
            _make_finding("f4", "uploaded", ["PIR-0"]),
        ]
        result = compute_collection_coverage(findings=findings, gaps=[], pirs=pirs)
        assert result.per_pir[0].score == pytest.approx(1.0, abs=0.01)
        assert result.per_pir[0].tier == ConfidenceTier.ASSESSED
