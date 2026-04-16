"""TDD tests for assertion-level confidence enrichment.

Tests are written against the enrichment logic in analysis_service.py
that maps PerspectiveAssertion.supporting_finding_ids → AssertionConfidence.
"""

import pytest

from src.models.analysis import FindingModel, ProcessingResult
from src.models.confidence import AssertionConfidence, ConfidenceTier, PerspectiveAssertion
from src.services.confidence.assertion_enrichment import enrich_assertions, validate_finding_ids


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    id: str,
    source: str,
    supporting_data: dict | None = None,
) -> FindingModel:
    return FindingModel(
        id=id,
        title=f"Finding {id}",
        finding="Body.",
        evidence_summary="Evidence.",
        source=source,
        confidence=70,
        relevant_to=[],
        supporting_data=supporting_data or {},
        why_it_matters="Matters.",
        uncertainties=[],
    )


def _make_assertion(text: str, finding_ids: list[str]) -> PerspectiveAssertion:
    return PerspectiveAssertion(
        assertion=text,
        supporting_finding_ids=finding_ids,
    )


# ---------------------------------------------------------------------------
# validate_finding_ids
# ---------------------------------------------------------------------------


class TestValidateFindingIds:
    """Invalid finding IDs are stripped; valid ones are kept."""

    def test_all_valid_ids_kept(self):
        assertions = [{"assertion": "A", "supporting_finding_ids": ["F-001", "F-002"]}]
        valid = {"F-001", "F-002"}
        result = validate_finding_ids(assertions, valid)
        assert result[0]["supporting_finding_ids"] == ["F-001", "F-002"]

    def test_invalid_ids_stripped(self):
        assertions = [{"assertion": "A", "supporting_finding_ids": ["F-001", "FAKE-99"]}]
        valid = {"F-001"}
        result = validate_finding_ids(assertions, valid)
        assert result[0]["supporting_finding_ids"] == ["F-001"]

    def test_all_invalid_ids_leaves_empty_list(self):
        assertions = [{"assertion": "A", "supporting_finding_ids": ["FAKE-1", "FAKE-2"]}]
        valid = {"F-001"}
        result = validate_finding_ids(assertions, valid)
        assert result[0]["supporting_finding_ids"] == []

    def test_empty_valid_set_strips_all(self):
        assertions = [{"assertion": "A", "supporting_finding_ids": ["F-001"]}]
        result = validate_finding_ids(assertions, set())
        assert result[0]["supporting_finding_ids"] == []

    def test_no_crash_on_missing_key(self):
        assertions = [{"assertion": "A"}]
        result = validate_finding_ids(assertions, {"F-001"})
        assert result[0].get("supporting_finding_ids", []) == []


# ---------------------------------------------------------------------------
# enrich_assertions — KB + OTX → multi-source HIGH
# ---------------------------------------------------------------------------


class TestEnrichAssertionsMultiSource:
    """Assertion backed by KB + OTX findings → HIGH or ASSESSED tier."""

    def test_confidence_is_set(self):
        findings = [
            _make_finding("F-001", "knowledge_bank"),
            _make_finding("F-002", "otx"),
        ]
        assertions = [_make_assertion("Some claim.", ["F-001", "F-002"])]
        enriched = enrich_assertions(assertions, findings)
        assert enriched[0].confidence is not None

    def test_confidence_is_assertion_confidence_type(self):
        findings = [
            _make_finding("F-001", "knowledge_bank"),
            _make_finding("F-002", "otx"),
        ]
        assertions = [_make_assertion("Some claim.", ["F-001", "F-002"])]
        enriched = enrich_assertions(assertions, findings)
        assert isinstance(enriched[0].confidence, AssertionConfidence)

    def test_tier_is_high_or_assessed(self):
        findings = [
            _make_finding("F-001", "knowledge_bank"),
            _make_finding("F-002", "otx"),
        ]
        assertions = [_make_assertion("Some claim.", ["F-001", "F-002"])]
        enriched = enrich_assertions(assertions, findings)
        assert enriched[0].confidence.tier in (ConfidenceTier.HIGH, ConfidenceTier.ASSESSED)

    def test_source_types_populated(self):
        findings = [
            _make_finding("F-001", "knowledge_bank"),
            _make_finding("F-002", "otx"),
        ]
        assertions = [_make_assertion("Some claim.", ["F-001", "F-002"])]
        enriched = enrich_assertions(assertions, findings)
        assert len(enriched[0].source_types) >= 2


# ---------------------------------------------------------------------------
# Zero valid finding IDs → LOW with pretrained authority
# ---------------------------------------------------------------------------


class TestEnrichAssertionsZeroFindings:
    """Assertion with zero valid findings → LOW, authority = pretrained."""

    def test_tier_is_low(self):
        findings = [_make_finding("F-001", "knowledge_bank")]
        assertions = [_make_assertion("Unsupported claim.", [])]
        enriched = enrich_assertions(assertions, findings)
        assert enriched[0].confidence.tier == ConfidenceTier.LOW

    def test_authority_is_pretrained(self):
        findings = [_make_finding("F-001", "knowledge_bank")]
        assertions = [_make_assertion("Unsupported claim.", [])]
        enriched = enrich_assertions(assertions, findings)
        assert enriched[0].confidence.authority == pytest.approx(0.10)

    def test_assertion_text_preserved(self):
        findings = []
        assertions = [_make_assertion("Original text.", [])]
        enriched = enrich_assertions(assertions, findings)
        assert enriched[0].assertion == "Original text."


# ---------------------------------------------------------------------------
# Circular reporting across findings
# ---------------------------------------------------------------------------


class TestCircularReportingInAssertions:
    """Two findings sharing a kb_ref → circular flag raised, score reduced."""

    def test_circular_flag_raised(self):
        findings = [
            _make_finding("F-001", "otx", supporting_data={"kb_refs": ["https://same.com/report"]}),
            _make_finding("F-002", "otx", supporting_data={"kb_refs": ["https://same.com/report"]}),
        ]
        assertions = [_make_assertion("Claim.", ["F-001", "F-002"])]
        enriched = enrich_assertions(assertions, findings)
        assert enriched[0].confidence.circular_flag is True

    def test_score_lower_with_circular(self):
        findings_circular = [
            _make_finding("F-001", "otx", supporting_data={"kb_refs": ["https://same.com/report"]}),
            _make_finding("F-002", "otx", supporting_data={"kb_refs": ["https://same.com/report"]}),
        ]
        findings_clean = [
            _make_finding("F-001", "otx", supporting_data={"kb_refs": ["https://report-a.com"]}),
            _make_finding("F-002", "otx", supporting_data={"kb_refs": ["https://report-b.com"]}),
        ]
        a_circular = [_make_assertion("Claim.", ["F-001", "F-002"])]
        a_clean = [_make_assertion("Claim.", ["F-001", "F-002"])]
        enriched_circular = enrich_assertions(a_circular, findings_circular)
        enriched_clean = enrich_assertions(a_clean, findings_clean)
        assert enriched_circular[0].confidence.score < enriched_clean[0].confidence.score


# ---------------------------------------------------------------------------
# Assertion text preserved through enrichment
# ---------------------------------------------------------------------------


class TestAssertionTextPreserved:
    def test_assertion_text_unchanged(self):
        findings = [_make_finding("F-001", "knowledge_bank")]
        original_text = "The adversary has pre-positioned in critical infrastructure."
        assertions = [_make_assertion(original_text, ["F-001"])]
        enriched = enrich_assertions(assertions, findings)
        assert enriched[0].assertion == original_text

    def test_supporting_finding_ids_preserved(self):
        findings = [_make_finding("F-001", "knowledge_bank")]
        assertions = [_make_assertion("Claim.", ["F-001"])]
        enriched = enrich_assertions(assertions, findings)
        assert "F-001" in enriched[0].supporting_finding_ids


# ---------------------------------------------------------------------------
# Multiple assertions enriched independently
# ---------------------------------------------------------------------------


class TestMultipleAssertions:
    def test_each_assertion_gets_confidence(self):
        findings = [
            _make_finding("F-001", "knowledge_bank"),
            _make_finding("F-002", "web_search"),
        ]
        assertions = [
            _make_assertion("Claim A.", ["F-001"]),
            _make_assertion("Claim B.", ["F-002"]),
            _make_assertion("Claim C.", []),
        ]
        enriched = enrich_assertions(assertions, findings)
        assert len(enriched) == 3
        assert all(a.confidence is not None for a in enriched)

    def test_low_source_differs_from_kb_source(self):
        findings = [
            _make_finding("F-001", "knowledge_bank"),
            _make_finding("F-002", "web_other"),
        ]
        assertions = [
            _make_assertion("High authority claim.", ["F-001"]),
            _make_assertion("Low authority claim.", ["F-002"]),
        ]
        enriched = enrich_assertions(assertions, findings)
        assert enriched[0].confidence.authority > enriched[1].confidence.authority
