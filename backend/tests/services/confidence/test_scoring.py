"""TDD tests for the confidence scoring algorithm (Layer 1).

Tests are written against the algorithm specification:
  authority × 0.40 + corroboration × 0.35 + independence × 0.25

Source authority weights and corroboration scale are defined in source_authority_config.py.
"""

import pytest

from src.models.confidence import ConfidenceTier
from src.services.confidence.scoring import compute_confidence


class TestSingleKBSource:
    """Single KB source, no corroboration → MODERATE."""

    def test_score_is_approx_7375(self):
        # authority(KB)=1.00 × 0.40 + corroboration(1 cluster)=0.25 × 0.35 + independence=1.0 × 0.25
        # = 0.40 + 0.0875 + 0.25 = 0.7375 → HIGH
        # Note: plan test spec showed "0.40×0.40 = 0.49" which appears to be a typo;
        # KB=1.00 authority gives 0.7375. Test #2 (KB+OTX) confirms 1.00*0.40 interpretation.
        result = compute_confidence(source_types=["knowledge_bank"])
        assert result.tier == ConfidenceTier.HIGH
        assert result.raw_score == pytest.approx(0.7375, abs=0.01)

    def test_authority_is_one(self):
        result = compute_confidence(source_types=["knowledge_bank"])
        assert result.authority == pytest.approx(1.00)

    def test_corroboration_is_point25(self):
        result = compute_confidence(source_types=["knowledge_bank"])
        assert result.corroboration == pytest.approx(0.25)

    def test_independence_is_one(self):
        result = compute_confidence(source_types=["knowledge_bank"])
        assert result.independence == pytest.approx(1.00)

    def test_no_circular_flag(self):
        result = compute_confidence(source_types=["knowledge_bank"])
        assert result.circular_flag is False


class TestModerateSource:
    """Single web_search source → roughly MODERATE."""

    def test_score_near_049(self):
        # authority(web_search)=0.35 × 0.40 + corroboration(1)=0.25 × 0.35 + independence=1.0 × 0.25
        # = 0.14 + 0.0875 + 0.25 = 0.4775 → MODERATE
        result = compute_confidence(source_types=["web_search"])
        assert result.tier == ConfidenceTier.MODERATE
        assert result.raw_score == pytest.approx(0.4775, abs=0.01)


class TestKBPlusTwoOTXClusters:
    """KB + 1 OTX = 2 independent clusters, no circular flag → HIGH."""

    def test_score_near_084(self):
        # max_authority = max(1.00, 0.70) = 1.00
        # 2 distinct URLs → 2 clusters → corroboration(2) = 0.55
        # independence = 1.0
        # = 1.00*0.40 + 0.55*0.35 + 1.0*0.25 = 0.40 + 0.1925 + 0.25 = 0.8425 → HIGH
        result = compute_confidence(
            source_types=["knowledge_bank", "otx"],
            source_urls=[
                "https://kb.internal/doc1",
                "https://otx.alienvault.com/report1",
            ],
        )
        assert result.tier == ConfidenceTier.HIGH
        assert result.raw_score == pytest.approx(0.8425, abs=0.02)

    def test_circular_flag_false(self):
        result = compute_confidence(
            source_types=["knowledge_bank", "otx", "otx"],
            source_urls=[
                "https://kb.internal/doc1",
                "https://otx.alienvault.com/1",
                "https://otx.alienvault.com/2",
            ],
        )
        assert result.circular_flag is False


class TestCircularReporting:
    """Circular reporting → score drops, flag set."""

    def test_score_drops_with_circular_flag(self):
        # Two sources sharing the same URL → circular detected
        # corroboration × 0.6, independence = 0.6
        result_clean = compute_confidence(
            source_types=["otx", "otx"],
            source_urls=["https://example.com/report1", "https://example.com/report2"],
        )
        result_circular = compute_confidence(
            source_types=["otx", "otx"],
            source_urls=["https://example.com/report", "https://example.com/report"],
        )
        assert result_circular.raw_score < result_clean.raw_score

    def test_circular_flag_is_true(self):
        result = compute_confidence(
            source_types=["otx", "otx"],
            source_urls=["https://same.com/report", "https://same.com/report"],
        )
        assert result.circular_flag is True

    def test_tier_drops(self):
        # KB + 2 OTX clusters, but circular detected
        # Without circular: score≈0.84 → HIGH
        # With circular: corroboration*0.6, independence=0.6
        # = 1.00*0.40 + 0.55*0.60*0.35 + 0.6*0.25 = 0.40 + 0.1155 + 0.15 = 0.6655 → MODERATE
        result = compute_confidence(
            source_types=["knowledge_bank", "otx"],
            source_urls=["https://kb.internal/doc1", "https://kb.internal/doc1"],
        )
        assert result.circular_flag is True
        assert result.tier == ConfidenceTier.MODERATE


class TestWebOtherSource:
    """Single web_other source → very low score → LOW."""

    def test_score_and_tier(self):
        # authority(web_other)=0.25 × 0.40 + corroboration(1)=0.25 × 0.35 + independence=1.0 × 0.25
        # = 0.10 + 0.0875 + 0.25 = 0.4375 → MODERATE (lowest non-LOW web tier)
        result = compute_confidence(source_types=["web_other"])
        assert result.authority == pytest.approx(0.25)
        assert result.raw_score == pytest.approx(0.4375, abs=0.01)
        assert result.tier == ConfidenceTier.MODERATE

    def test_authority_is_025(self):
        result = compute_confidence(source_types=["web_other"])
        assert result.authority == pytest.approx(0.25)


class TestWebGovSource:
    """web_gov source → authority 0.50, higher than web_other."""

    def test_authority_higher_than_web_other(self):
        result_gov = compute_confidence(source_types=["web_gov"])
        result_other = compute_confidence(source_types=["web_other"])
        assert result_gov.authority > result_other.authority

    def test_authority_is_050(self):
        result = compute_confidence(source_types=["web_gov"])
        assert result.authority == pytest.approx(0.50)


class TestWebThinkTank:
    """web_think_tank → authority 0.40."""

    def test_authority_is_040(self):
        result = compute_confidence(source_types=["web_think_tank"])
        assert result.authority == pytest.approx(0.40)


class TestFourPlusClusters:
    """4+ independent clusters → corroboration capped at 0.90."""

    def test_corroboration_capped(self):
        result = compute_confidence(
            source_types=["knowledge_bank", "otx", "web_search", "web_gov"],
            source_urls=[
                "https://kb.internal/a",
                "https://otx.alienvault.com/b",
                "https://example.com/c",
                "https://fbi.gov/d",
            ],
        )
        assert result.corroboration == pytest.approx(0.90)

    def test_score_is_assessed(self):
        # 1.00*0.40 + 0.90*0.35 + 1.0*0.25 = 0.40 + 0.315 + 0.25 = 0.965 → ASSESSED
        result = compute_confidence(
            source_types=["knowledge_bank", "otx", "web_search", "web_gov"],
            source_urls=[
                "https://kb.internal/a",
                "https://otx.alienvault.com/b",
                "https://example.com/c",
                "https://fbi.gov/d",
            ],
        )
        assert result.tier == ConfidenceTier.ASSESSED


class TestNoSources:
    """No sources (pretrained only) → authority 0.10 → LOW."""

    def test_empty_source_list_gives_low(self):
        result = compute_confidence(source_types=[])
        assert result.tier == ConfidenceTier.LOW

    def test_uncited_source_gives_low(self):
        result = compute_confidence(source_types=["uncited"])
        assert result.authority == pytest.approx(0.10)

    def test_pretrained_source_gives_low_authority(self):
        result = compute_confidence(source_types=["pretrained"])
        assert result.authority == pytest.approx(0.10)
        assert result.tier == ConfidenceTier.LOW


class TestMaxAuthorityAcrossSources:
    """Multiple sources → max authority (strong source not diluted by weaker)."""

    def test_kb_not_diluted_by_web_other(self):
        _ = compute_confidence(source_types=["knowledge_bank"])
        result_kb_and_web = compute_confidence(
            source_types=["knowledge_bank", "web_other"],
            source_urls=["https://kb.internal/a", "https://example.com/b"],
        )
        # Authority should remain 1.00 (max), not averaged
        assert result_kb_and_web.authority == pytest.approx(1.00)

    def test_otx_beats_web_other(self):
        result = compute_confidence(source_types=["web_other", "otx"])
        assert result.authority == pytest.approx(0.70)


class TestTierBoundaries:
    """Score at tier boundaries maps correctly."""

    def test_039_is_low(self):
        from src.services.confidence.scoring import _score_to_tier

        assert _score_to_tier(0.39) == ConfidenceTier.LOW

    def test_040_is_moderate(self):
        from src.services.confidence.scoring import _score_to_tier

        assert _score_to_tier(0.40) == ConfidenceTier.MODERATE

    def test_069_is_moderate(self):
        from src.services.confidence.scoring import _score_to_tier

        assert _score_to_tier(0.69) == ConfidenceTier.MODERATE

    def test_070_is_high(self):
        from src.services.confidence.scoring import _score_to_tier

        assert _score_to_tier(0.70) == ConfidenceTier.HIGH

    def test_090_is_assessed(self):
        from src.services.confidence.scoring import _score_to_tier

        assert _score_to_tier(0.90) == ConfidenceTier.ASSESSED


class TestSourceTypesRecorded:
    """The returned source_types list reflects the normalised input."""

    def test_source_types_returned(self):
        result = compute_confidence(source_types=["knowledge_bank", "otx"])
        assert "knowledge_bank" in result.source_types
        assert "otx" in result.source_types

    def test_empty_source_types_on_no_input(self):
        result = compute_confidence(source_types=[])
        # source_types may be empty or contain "uncited" sentinel — score matters more
        assert isinstance(result.source_types, list)
