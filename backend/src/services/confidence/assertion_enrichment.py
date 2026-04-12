"""Assertion-level confidence enrichment (Layer 3).

Pure functions that take a list of PerspectiveAssertion objects and the available
FindingModel list and return enriched assertions with AssertionConfidence attached.

No AI calls. No IO.
"""

import logging

from src.models.analysis import FindingModel
from src.models.confidence import AssertionConfidence, ConfidenceTier, PerspectiveAssertion
from src.services.confidence.scoring import compute_confidence, detect_circular_reporting
from src.services.confidence.source_authority_config import SOURCE_AUTHORITY_WEIGHTS

logger = logging.getLogger(__name__)

_PRETRAINED_AUTHORITY = SOURCE_AUTHORITY_WEIGHTS.get("pretrained", 0.10)

# Fallback confidence for zero-finding assertions (no evidence base)
_ZERO_FINDING_CONFIDENCE = AssertionConfidence(
    tier=ConfidenceTier.LOW,
    score=round(_PRETRAINED_AUTHORITY * 0.40 + 0.25 * 0.35 + 1.0 * 0.25, 4),
    authority=_PRETRAINED_AUTHORITY,
    corroboration=0.25,
    independence=1.0,
    circular_flag=False,
)


def validate_finding_ids(
    assertions: list[dict],
    valid_finding_ids: set[str],
) -> list[dict]:
    """Strip invalid finding IDs from raw assertion dicts and log warnings.

    Args:
        assertions: List of raw assertion dicts (from AI output or fallback).
                    Each dict may have a 'supporting_finding_ids' key.
        valid_finding_ids: Set of finding IDs that exist in the ProcessingResult.

    Returns:
        Same list with invalid IDs stripped from 'supporting_finding_ids'.
    """
    for assertion in assertions:
        original = assertion.get("supporting_finding_ids") or []
        valid = [fid for fid in original if fid in valid_finding_ids]
        stripped = len(original) - len(valid)
        if stripped > 0:
            logger.warning(
                "Stripped %d invalid finding ID(s) from assertion: %s",
                stripped,
                assertion.get("assertion", "")[:80],
            )
        assertion["supporting_finding_ids"] = valid
    return assertions


def enrich_assertions(
    assertions: list[PerspectiveAssertion],
    findings: list[FindingModel],
) -> list[PerspectiveAssertion]:
    """Compute and attach AssertionConfidence for each PerspectiveAssertion.

    Args:
        assertions: List of assertions (may have empty/None confidence).
        findings: All available findings from ProcessingResult.

    Returns:
        New list of PerspectiveAssertion objects with confidence populated.
    """
    finding_by_id: dict[str, FindingModel] = {f.id: f for f in findings}
    enriched: list[PerspectiveAssertion] = []

    for assertion in assertions:
        # Resolve supporting findings
        supporting: list[FindingModel] = [
            finding_by_id[fid]
            for fid in assertion.supporting_finding_ids
            if fid in finding_by_id
        ]

        if not supporting:
            # No evidence base → pretrained/uncited authority, LOW tier
            confidence = _ZERO_FINDING_CONFIDENCE
            source_types: list[str] = []
        else:
            source_types = _collect_source_types(supporting)
            source_urls = _collect_source_urls(supporting)
            circular = _check_circular_across_findings(supporting)

            breakdown = compute_confidence(
                source_types=source_types,
                source_urls=source_urls if source_urls else None,
            )
            # Override circular flag if cross-finding refs share URLs
            if circular and not breakdown.circular_flag:
                # Re-compute with circular penalty applied manually
                from src.services.confidence.scoring import (
                    _CIRCULAR_MULTIPLIER,
                    _W_AUTHORITY,
                    _W_CORROBORATION,
                    _W_INDEPENDENCE,
                    _score_to_tier,
                )

                corroboration_penalised = breakdown.corroboration * _CIRCULAR_MULTIPLIER
                independence_penalised = _CIRCULAR_MULTIPLIER
                raw = round(
                    breakdown.authority * _W_AUTHORITY
                    + corroboration_penalised * _W_CORROBORATION
                    + independence_penalised * _W_INDEPENDENCE,
                    4,
                )
                confidence = AssertionConfidence(
                    tier=_score_to_tier(raw),
                    score=raw,
                    authority=round(breakdown.authority, 4),
                    corroboration=round(corroboration_penalised, 4),
                    independence=round(independence_penalised, 4),
                    circular_flag=True,
                )
            else:
                confidence = AssertionConfidence(
                    tier=ConfidenceTier(breakdown.tier),
                    score=breakdown.raw_score,
                    authority=round(breakdown.authority, 4),
                    corroboration=round(breakdown.corroboration, 4),
                    independence=round(breakdown.independence, 4),
                    circular_flag=breakdown.circular_flag,
                )

        enriched.append(
            PerspectiveAssertion(
                assertion=assertion.assertion,
                supporting_finding_ids=assertion.supporting_finding_ids,
                source_types=source_types,
                confidence=confidence,
            )
        )

    return enriched


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_source_types(findings: list[FindingModel]) -> list[str]:
    """Unique source type strings from a set of findings."""
    seen: set[str] = set()
    types: list[str] = []
    for f in findings:
        s = f.source.lower().strip()
        if s not in seen:
            seen.add(s)
            types.append(s)
    return types


def _collect_source_urls(findings: list[FindingModel]) -> list[str]:
    """Extract URLs from supporting_data.source_refs across findings."""
    urls: list[str] = []
    for f in findings:
        refs = f.supporting_data.get("source_refs") or []
        urls.extend(refs)
    return urls


def _check_circular_across_findings(findings: list[FindingModel]) -> bool:
    """True if two or more findings share a kb_refs URL (cross-finding circular)."""
    all_refs: list[str] = []
    for f in findings:
        kb_refs = f.supporting_data.get("kb_refs") or []
        all_refs.extend(r.strip().lower() for r in kb_refs if r.strip())
    if len(all_refs) < 2:
        return False
    return len(all_refs) != len(set(all_refs))
