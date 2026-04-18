"""Analysis Confidence Score — deterministic algorithm.

No AI calls. Pure functions that compute confidence from source metadata.

Formula: authority × 0.40 + corroboration × 0.35 + independence × 0.25

Theoretical grounding:
- JDP 2-00 pp. 59–60: Source reliability and information credibility are
  separate dimensions. Authority weights implement the reliability dimension.
- JDP 2-00 p. 32: Assessments must be bounded by uncertainty — corroboration
  is capped at 0.90.
- JDP 2-00 p. 59 §3.39: Circular reporting warning — independence component
  with 0.6 multiplier implements this.
"""

from urllib.parse import urlparse

from src.models.confidence import ConfidenceBreakdown, ConfidenceTier
from src.services.confidence.source_authority_config import (
    CORROBORATION_CAP,
    CORROBORATION_SCALE,
    GOV_EXACT_DOMAINS,
    GOV_PATTERNS,
    GOV_SUFFIX_PATTERNS,
    NEWS_DOMAINS,
    SOURCE_AUTHORITY_WEIGHTS,
    STATE_MEDIA_DOMAINS,
    THINK_TANK_DOMAINS,
)

# ---------------------------------------------------------------------------
# Component weights
# ---------------------------------------------------------------------------

_W_AUTHORITY = 0.40
_W_CORROBORATION = 0.35
_W_INDEPENDENCE = 0.25

# Circular-reporting penalty multiplier (JDP 2-00 §3.39)
_CIRCULAR_MULTIPLIER = 0.6


# ---------------------------------------------------------------------------
# Tier mapping (shared with collection_coverage.py)
# ---------------------------------------------------------------------------


def _score_to_tier(score: float) -> ConfidenceTier:
    if score >= 0.90:
        return ConfidenceTier.ASSESSED
    if score >= 0.70:
        return ConfidenceTier.HIGH
    if score >= 0.40:
        return ConfidenceTier.MODERATE
    return ConfidenceTier.LOW


# ---------------------------------------------------------------------------
# URL / domain helpers
# ---------------------------------------------------------------------------


def _extract_domain(url: str) -> str:
    """Extract the lowercase netloc from a URL string."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc or parsed.path
        # Strip port and leading 'www.'
        host = host.split(":")[0].lower().strip()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return url.lower().strip()


def classify_web_source(url: str | None, publisher: str | None) -> str:  # noqa: ARG001
    """Classify a web source URL into an authority tier string.

    Priority order: state_media → gov_pattern → gov_exact → think_tank → news → other.
    Returns one of: web_gov, web_think_tank, web_news, web_other.
    """
    if not url:
        return "web_other"

    domain = _extract_domain(url)
    if not domain:
        return "web_other"

    # 1. State media → treat as government authority
    if any(sm in domain for sm in STATE_MEDIA_DOMAINS):
        return "web_gov"

    # 2. Government — pattern-based (.gov., .mil., etc.)
    if any(pattern in domain for pattern in GOV_PATTERNS):
        return "web_gov"

    # 3. Government — suffix patterns (.gov, .mil at end of domain)
    if any(domain.endswith(suffix) for suffix in GOV_SUFFIX_PATTERNS):
        return "web_gov"

    # 4. Government — exact domain match
    if any(domain == g or domain.endswith("." + g) for g in GOV_EXACT_DOMAINS):
        return "web_gov"

    # 5. Think tanks
    if any(t in domain for t in THINK_TANK_DOMAINS):
        return "web_think_tank"

    # 6. News
    if any(n in domain for n in NEWS_DOMAINS):
        return "web_news"

    return "web_other"


# ---------------------------------------------------------------------------
# Authority component
# ---------------------------------------------------------------------------


def _compute_authority(
    source_types: list[str],
    source_urls: list[str] | None,
) -> float:
    """Max authority across all sources. One strong source is not diluted."""
    if not source_types:
        return SOURCE_AUTHORITY_WEIGHTS.get("uncited", 0.10)

    authority_values: list[float] = []
    urls = source_urls or []

    for i, src in enumerate(source_types):
        src_lower = src.lower().strip()

        # For web_search sources, try to classify the URL more precisely
        if src_lower in ("web_search", "web") and i < len(urls):
            classified = classify_web_source(urls[i], None)
            authority = SOURCE_AUTHORITY_WEIGHTS.get(classified, 0.25)
        else:
            authority = SOURCE_AUTHORITY_WEIGHTS.get(
                src_lower, SOURCE_AUTHORITY_WEIGHTS.get("uncited", 0.10)
            )

        authority_values.append(authority)

    return max(authority_values) if authority_values else 0.10


# ---------------------------------------------------------------------------
# Corroboration component
# ---------------------------------------------------------------------------


def _count_independent_clusters(source_urls: list[str] | None) -> int:
    """Count distinct URL clusters. Sources sharing the same URL → 1 cluster."""
    if not source_urls:
        return 1  # assume at least one source cluster

    unique_urls = {u.strip().lower() for u in source_urls if u.strip()}
    return max(len(unique_urls), 1)


def _compute_corroboration(cluster_count: int) -> float:
    return CORROBORATION_SCALE.get(cluster_count, CORROBORATION_CAP)


# ---------------------------------------------------------------------------
# Circular reporting detection
# ---------------------------------------------------------------------------


def detect_circular_reporting(
    source_urls: list[str] | None,
) -> bool:
    """True if two or more sources share the same reference URL."""
    if not source_urls or len(source_urls) < 2:
        return False
    normalized = [u.strip().lower() for u in source_urls if u.strip()]
    return len(normalized) != len(set(normalized))


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------


def compute_confidence(
    source_types: list[str],
    source_urls: list[str] | None = None,
    _source_publishers: list[str] | None = None,
) -> ConfidenceBreakdown:
    """Compute structured confidence from source metadata.

    Args:
        source_types: List of source type strings (e.g. ["knowledge_bank", "otx"]).
                      Unknown strings fall back to "uncited" authority (0.10).
        source_urls:  Parallel list of URLs for each source. Used for URL-based
                      classification of web sources and corroboration clustering.
        source_publishers: Unused currently; reserved for future publisher metadata.

    Returns:
        ConfidenceBreakdown with authority, corroboration, independence, raw_score,
        tier, source_types, circular_flag.
    """
    # 1. Authority (max across sources)
    authority = _compute_authority(source_types, source_urls)

    # 2. Corroboration (distinct clusters)
    cluster_count = _count_independent_clusters(source_urls)
    if not source_types:
        cluster_count = 1
    corroboration_raw = _compute_corroboration(cluster_count)

    # 3. Circular reporting
    circular_flag = detect_circular_reporting(source_urls)

    if circular_flag:
        corroboration = corroboration_raw * _CIRCULAR_MULTIPLIER
        independence = _CIRCULAR_MULTIPLIER
    else:
        corroboration = corroboration_raw
        independence = 1.0

    # 4. Combine
    raw_score = round(
        authority * _W_AUTHORITY
        + corroboration * _W_CORROBORATION
        + independence * _W_INDEPENDENCE,
        4,
    )

    tier = _score_to_tier(raw_score)

    return ConfidenceBreakdown(
        authority=round(authority, 4),
        corroboration=round(corroboration, 4),
        independence=round(independence, 4),
        raw_score=raw_score,
        tier=tier.value,
        source_types=list(source_types),
        circular_flag=circular_flag,
    )
