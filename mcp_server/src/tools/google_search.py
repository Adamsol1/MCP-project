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

_NOISE_SITES = [
    "reddit.com",
    "x.com",
    "twitter.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "quora.com",
    "pinterest.com",
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
    }
    if date_restrict:
        unit = date_restrict[0]  # d/w/m/y
        payload["tbs"] = f"qdr:{unit}"
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
    num_results: int = 5,
    date_restrict: str | None = None,
    region: str | None = None,
    language: str | None = None,
) -> str:
    """Search Google for open-source threat intelligence via Serper.

    Returns titles, URLs, and snippets as formatted plain text.
    Social media and noise sites (Reddit, X, Facebook, etc.) are excluded automatically.
    Source authority: LOWER than OTX — use for recent events or when OTX is sparse.

    Parameters:
    - query: Search query. Include perspective context directly in the query text.
             Examples:
               "APT29 Norway perspective recent activity"
               "Russia GPS jamming Nordic region 2025"
               "China economic reaction US Iran attack"
    - num_results: Number of results to return (1-10, default 5).
    - date_restrict: Restrict results to a time window:
                     "d1" = last day, "w1" = last week, "m1" = last month,
                     "m3" = last 3 months, "m6" = last 6 months, "y1" = last year.
                     Omit for no time restriction.
    - region: Serper gl parameter for geolocation bias.
              Perspective mapping:
                us      → "us"   eu      → "gb"   norway  → "no"
                china   → "cn"   russia  → "ru"   neutral → omit
    - language: Serper hl parameter for language bias.
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


def fetch_page(url: str, max_chars: int = 5000) -> str:
    """Fetch and extract readable text content from a web page URL.

    Use after google_search or google_news_search to get the full content of
    the most relevant articles. Only call on 2-3 highest-value URLs per
    perspective — do not fetch every result, only where the snippet is
    insufficient to assess relevance or extract key facts.

    Parameters:
    - url: The full URL to fetch.
    - max_chars: Maximum characters to return (default 5000, max 10000).
    """
    from bs4 import BeautifulSoup

    max_chars = min(max(500, max_chars), 10000)

    try:
        with httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ThreatIntelBot/1.0)"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "form", "iframe", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)

        truncated = len(text) > max_chars
        text = text[:max_chars]

        suffix = "\n[content truncated]" if truncated else ""
        return f"[fetch_page] Content from: {url}\n\n{text}{suffix}"

    except httpx.HTTPStatusError as e:
        return f"[fetch_page] HTTP {e.response.status_code}: {url}"
    except httpx.TimeoutException:
        return f"[fetch_page] Timeout fetching: {url}"
    except Exception as e:
        return f"[fetch_page] Error: {e}"


def register_google_search_tools(mcp) -> None:
    mcp.tool(google_search)
    mcp.tool(google_news_search)
    mcp.tool(fetch_page)
