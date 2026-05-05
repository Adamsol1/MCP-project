"""Google Search and Google News MCP tools powered by Serper.dev.

Estimated usage: ~5 web + ~5 news queries per perspective per collection attempt.
A 3-perspective session uses roughly 30 queries total.
"""

import logging
import os

import httpx

logger = logging.getLogger("app")

_SERPER_SEARCH_URL = "https://google.serper.dev/search"
_SERPER_NEWS_URL = "https://google.serper.dev/news"

# Domains appended to every Serper query as -site: exclusions.
# Serper evaluates these server-side, so they cost no extra results slots.
# Add to this list whenever low-quality domains recur in raw collected_data.
_NOISE_SITES = [
    # Social media
    "reddit.com",
    "x.com",
    "twitter.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "quora.com",
    "pinterest.com",
    "linkedin.com",
    # Wiki / user-generated encyclopaedias (non-Wikipedia)
    "namu.wiki",
    "fandom.com",
    "wikia.com",
    # Generic blog / personal page platforms
    "blogspot.com",
    "wordpress.com",
    "medium.com",
    "substack.com",
    "github.io",
    # Job boards and career sites
    "indeed.com",
    "glassdoor.com",
    # Financial / market noise
    "stocktitan.net",
    "seekingalpha.com",
    "zerohedge.com",
    # Shopping and e-commerce
    "amazon.com",
    "ebay.com",
    "alibaba.com",
    # Low-signal aggregators and link farms
    "researchandmarkets.com",
    "globenewswire.com",
    "prnewswire.com",
    "businesswire.com",
]
_SITE_EXCLUSION = " ".join(f"-site:{s}" for s in _NOISE_SITES)


def _build_serper_payload(
    query: str,
    num_results: int,
    date_restrict: str | None,
    region: str | None,
    language: str | None,
) -> dict:
    payload: dict = {
        "q": f"{query} {_SITE_EXCLUSION}",
        "num": min(max(1, num_results), 10),
        # Always restrict to English-language pages so analysts can read results.
        # Geographic perspective is preserved via the `gl` (region) parameter.
        "lr": "lang_en",
    }
    if date_restrict:
        payload["tbs"] = f"qdr:{date_restrict}"
    if region:
        payload["gl"] = region
    if language:
        payload["hl"] = language
    return payload


def _serper_headers() -> dict:
    return {
        "X-API-KEY": os.getenv("SERPER_API_KEY", ""),
        "Content-Type": "application/json",
    }


def _handle_serper_error(e: Exception) -> str | None:
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 403:
            return "Error: Serper API key invalid or quota exceeded (HTTP 403)."
        if status == 429:
            return "Error: Serper rate limit hit — retry after a short delay."
        return f"Error: HTTP {status}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out."
    return f"Error: {e}"


def google_search(
    query: str,
    num_results: int = 10,
    date_restrict: str | None = None,
    region: str | None = None,
    language: str | None = None,
) -> str:
    """Search Google for open-source threat intelligence via Serper.

    Returns URLs and snippets as formatted plain text for URL discovery only.
    The backend will fetch and summarise the full content of each page separately —
    do NOT treat snippets as final intelligence. Focus on targeted queries that
    surface relevant, authoritative source URLs.
    Social media and noise sites (Reddit, X, Facebook, etc.) are excluded automatically.
    Source authority: LOWER than OTX — use for recent events or when OTX is sparse.

    Parameters:
    - query: Search query. Include perspective context directly in the query text.
             Examples:
               "APT29 Norway perspective recent activity"
               "Russia GPS jamming Nordic region 2025"
               "China economic reaction US Iran attack"
    - num_results: Number of results to return (1-10, default 10).
    - date_restrict: Restrict results to a time window:
                     "d1" = last day, "w1" = last week, "m1" = last month,
                     "m3" = last 3 months, "m6" = last 6 months, "y1" = last year.
                     Omit for no time restriction.
    - region: Serper gl parameter for geolocation bias.
              Perspective mapping:
                us      → "us"   eu      → "gb"   norway  → "no"
                china   → "cn"   russia  → "ru"   neutral → omit
    - language: Serper hl parameter for interface language bias (affects ranking, not
                result language — results are always restricted to English via lr=lang_en).
                Perspective mapping:
                us      → "en"   eu      → "en"   norway  → "no"
                china   → "zh-cn" russia → "ru"   neutral → omit
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return (
            "[google_search] Error: Serper is not configured. "
            "Set the SERPER_API_KEY environment variable."
        )

    payload = _build_serper_payload(query, num_results, date_restrict, region, language)

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(_SERPER_SEARCH_URL, json=payload, headers=_serper_headers())
            response.raise_for_status()
            data = response.json()

        items = data.get("organic", [])
        if not items:
            return f"[google_search] No results found for query: {query}"

        lines = [f"[google_search] Results for: {query}"]
        for i, item in enumerate(items, 1):
            lines.append(f"\n[{i}] {item.get('title', '')}")
            lines.append(f"    URL: {item.get('link', '')}")
            lines.append(f"    Snippet: {item.get('snippet', '').replace(chr(10), ' ')}")
        return "\n".join(lines)

    except Exception as e:
        err = _handle_serper_error(e)
        return f"[google_search] {err or e}"


def google_news_search(
    query: str,
    num_results: int = 5,
    date_restrict: str | None = None,
    region: str | None = None,
    language: str | None = None,
) -> str:
    """Search Google News for recent threat intelligence via Serper.

    Returns news article titles, URLs, sources, publication dates, and snippets.
    Use this alongside google_search — news gives recent/breaking coverage while
    web search gives deeper background reports.
    Social media and noise sites are excluded automatically.
    Source authority: LOWER than OTX.

    Parameters:
    - query: Search query. Include perspective context directly in the query text.
             Examples:
               "APT29 Norway perspective latest"
               "Russia cyberattack energy sector 2025"
    - num_results: Number of results to return (1-10, default 5).
    - date_restrict: Restrict results to a time window:
                     "d1" = last day, "w1" = last week, "m1" = last month,
                     "m3" = last 3 months, "m6" = last 6 months, "y1" = last year.
    - region: Serper gl parameter for geolocation bias (same mapping as google_search).
    - language: Serper hl parameter for language bias (same mapping as google_search).
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return (
            "[google_news_search] Error: Serper is not configured. "
            "Set the SERPER_API_KEY environment variable."
        )

    payload = _build_serper_payload(query, num_results, date_restrict, region, language)

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(_SERPER_NEWS_URL, json=payload, headers=_serper_headers())
            response.raise_for_status()
            data = response.json()

        items = data.get("news", [])
        if not items:
            return f"[google_news_search] No results found for query: {query}"

        lines = [f"[google_news_search] News results for: {query}"]
        for i, item in enumerate(items, 1):
            lines.append(f"\n[{i}] {item.get('title', '')}")
            lines.append(f"    URL: {item.get('link', '')}")
            lines.append(f"    Source: {item.get('source', '')}  Date: {item.get('date', '')}")
            lines.append(f"    Snippet: {item.get('snippet', '').replace(chr(10), ' ')}")
        return "\n".join(lines)

    except Exception as e:
        err = _handle_serper_error(e)
        return f"[google_news_search] {err or e}"


def register_google_search_tools(mcp) -> None:
    mcp.tool(google_search)
