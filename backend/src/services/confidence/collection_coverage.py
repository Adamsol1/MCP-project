"""Deterministic Collection Coverage Confidence Score.

No AI calls. Pure function that maps (findings, gaps, PIRs) → CollectionCoverageResult.

Theoretical grounding:
- JDP 2-00 pp. 63–66: Analytical confidence depends on breadth and quality of evidence.
- JDP 2-00 p. 59: Source reliability and information credibility are separate dimensions.
- Borg (2017): Gaps and limitations must be explicit, not hidden.
"""

from src.models.analysis import FindingModel
from src.models.confidence import (
    CollectionCoverageResult,
    ConfidenceTier,
    CoverageFindingRef,
    PirCoverageScore,
)

# ---------------------------------------------------------------------------
# Source type normalisation
# ---------------------------------------------------------------------------

SOURCE_TYPE_MAP: dict[str, str] = {
    "osint": "otx",
    "otx": "otx",
    "knowledge_bank": "knowledge_bank",
    "knowledge_base": "knowledge_bank",
    "web_search": "web_search",
    "web": "web_search",
    "network_telemetry": "uploaded",
    "malware_analysis": "uploaded",
    "manual": "uploaded",
    "uploaded": "uploaded",
}


def _normalise_source(source: str) -> str:
    return SOURCE_TYPE_MAP.get(source.lower().strip(), "other")


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

_PRIORITY_WEIGHTS: dict[str, int] = {"high": 3, "medium": 2, "low": 1}


def _score_to_tier(score: float) -> ConfidenceTier:
    """Map a 0–1 raw score to a ConfidenceTier."""
    if score >= 0.90:
        return ConfidenceTier.ASSESSED
    if score >= 0.70:
        return ConfidenceTier.HIGH
    if score >= 0.40:
        return ConfidenceTier.MODERATE
    return ConfidenceTier.LOW


def _coverage_score(finding_count: int) -> float:
    if finding_count == 0:
        return 0.00
    if finding_count == 1:
        return 0.50
    if finding_count == 2:
        return 0.75
    return 1.00


def _diversity_score(source_type_count: int) -> float:
    if source_type_count <= 0:
        return 0.00
    if source_type_count == 1:
        return 0.30
    if source_type_count == 2:
        return 0.65
    if source_type_count == 3:
        return 0.90
    return 1.00


def _gap_penalty_score(has_gap: bool) -> float:
    return 0.20 if has_gap else 1.00


def _has_gap_mention(pir_question: str, gaps: list[str]) -> bool:
    """True if any gap string shares a significant word with the PIR question."""
    # Extract words of 4+ characters from the PIR question (lowercase) as significant tokens.
    pir_words = {
        word.strip(".,;:()?!\"'")
        for word in pir_question.lower().split()
        if len(word.strip(".,;:()?!\"'")) >= 4
    }
    for gap in gaps:
        gap_lower = gap.lower()
        if any(word in gap_lower for word in pir_words):
            return True
    return False


def _build_rationale(
    pir_index: int,  # noqa: ARG001
    priority: str,
    tier: ConfidenceTier,
    finding_count: int,
    source_type_count: int,
    has_gap: bool,
    score: float,
) -> str:
    parts: list[str] = []

    if priority == "high" and tier in (ConfidenceTier.LOW, ConfidenceTier.MODERATE):
        parts.append("⚠ HIGH-PRIORITY PIR")

    parts.append(
        f"{finding_count} finding{'s' if finding_count != 1 else ''} mapped"
        f" from {source_type_count} source type{'s' if source_type_count != 1 else ''}."
    )

    if has_gap:
        parts.append("An identified gap references this PIR's topic.")

    tier_label = tier.value.capitalize()
    parts.append(f"Coverage tier: {tier_label} (score {score:.2f}).")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_collection_coverage(
    findings: list[FindingModel],
    gaps: list[str],
    pirs: list[dict],
) -> CollectionCoverageResult:
    """Compute deterministic collection coverage scores for each PIR.

    Args:
        findings: Processed findings from ProcessingResult.findings.
        gaps: Outstanding gaps from ProcessingResult.gaps.
        pirs: Approved PIRs from Direction phase. Each dict must have:
              'question' (str), 'priority' (str), 'rationale' (str).

    Returns:
        CollectionCoverageResult with per-PIR scores and an aggregate.
    """
    if not pirs:
        return CollectionCoverageResult(
            per_pir=[],
            aggregate_tier=ConfidenceTier.LOW,
            aggregate_score=0.0,
            summary="No PIRs defined — collection coverage cannot be assessed.",
        )

    # Build a mapping: pir_key (e.g. "PIR-0") → list of findings
    pir_findings: dict[str, list[FindingModel]] = {
        f"PIR-{i}": [] for i in range(len(pirs))
    }
    for finding in findings:
        for ref in finding.relevant_to:
            if ref in pir_findings:
                pir_findings[ref].append(finding)

    per_pir: list[PirCoverageScore] = []
    for i, pir in enumerate(pirs):
        pir_key = f"PIR-{i}"
        pir_question: str = pir.get("question", "")
        priority: str = pir.get("priority", "medium").lower()

        mapped_findings = pir_findings[pir_key]
        finding_count = len(mapped_findings)

        # Source diversity
        canonical_types = {_normalise_source(f.source) for f in mapped_findings}
        source_types = sorted(canonical_types)

        # Gap flag
        has_gap = _has_gap_mention(pir_question, gaps)

        # Dimensional scores
        cov = _coverage_score(finding_count)
        div = _diversity_score(len(source_types))
        gap = _gap_penalty_score(has_gap)

        raw_score = round(cov * 0.45 + div * 0.35 + gap * 0.20, 4)
        tier = _score_to_tier(raw_score)

        rationale = _build_rationale(
            pir_index=i,
            priority=priority,
            tier=tier,
            finding_count=finding_count,
            source_type_count=len(source_types),
            has_gap=has_gap,
            score=raw_score,
        )

        finding_refs = [
            CoverageFindingRef(id=f.id, title=f.title, source=f.source)
            for f in mapped_findings
        ]

        per_pir.append(
            PirCoverageScore(
                pir_index=i,
                pir_question=pir_question,
                priority=priority,
                tier=tier,
                score=raw_score,
                finding_count=finding_count,
                source_types=source_types,
                has_gap_flag=has_gap,
                rationale=rationale,
                findings=finding_refs,
            )
        )

    # Weighted aggregate
    total_weight = 0.0
    weighted_sum = 0.0
    for ps in per_pir:
        w = float(_PRIORITY_WEIGHTS.get(ps.priority, 1))
        weighted_sum += ps.score * w
        total_weight += w

    aggregate_score = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0
    aggregate_tier = _score_to_tier(aggregate_score)

    # Human-readable summary
    low_count = sum(1 for ps in per_pir if ps.tier == ConfidenceTier.LOW)
    high_priority_low = [
        ps
        for ps in per_pir
        if ps.priority == "high"
        and ps.tier in (ConfidenceTier.LOW, ConfidenceTier.MODERATE)
    ]

    if low_count == len(per_pir):
        summary = "Collection coverage is insufficient — all PIRs lack adequate supporting findings."
    elif high_priority_low:
        summary = (
            f"Collection coverage is {aggregate_tier.value} overall; "
            f"{len(high_priority_low)} high-priority PIR(s) have low or moderate coverage."
        )
    else:
        summary = (
            f"Collection coverage is {aggregate_tier.value} "
            f"(score {aggregate_score:.2f}) across {len(per_pir)} PIR(s)."
        )

    return CollectionCoverageResult(
        per_pir=per_pir,
        aggregate_tier=aggregate_tier,
        aggregate_score=aggregate_score,
        summary=summary,
    )
