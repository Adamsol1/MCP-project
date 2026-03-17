import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException, RatelimitException

# Discussion/social sites excluded from all queries — too noisy for OSINT
_EXCLUDED_DOMAINS = [
    "reddit.com",
    "quora.com",
    "stackexchange.com",
    "stackoverflow.com",
    "facebook.com",
    "twitter.com",
    "x.com",
]
_EXCLUDE_SUFFIX = " " + " ".join(f"-site:{d}" for d in _EXCLUDED_DOMAINS)


def web_search(query: str, max_results: int = 3, timelimit: str | None = None, region: str = "wt-wt") -> str:
    """
    Search the web via DuckDuckGo for current open-source threat intelligence.
    Returns titles, URLs, and snippets as formatted plain text.
    Use for: recent CVEs, threat actor activity, campaign reports not in OTX.
    Source authority: LOWER than OTX — treat as corroborating/discovery only.
    Follow up with fetch_page() to retrieve full article content when needed.

    IMPORTANT: Always use region="wt-wt" (worldwide English). To search from a
    geopolitical perspective, include the perspective in the query text instead,
    e.g. "APT29 activity Norway perspective" or "Russia GPS jamming Nordic region".

    Parameters:
    - query: The search query string. Include perspective/region context in the query text.
    - max_results: Maximum number of results to return (default 3).
    - timelimit: DDG time filter — "d"=day, "w"=week, "m"=month, "y"=year, None=no limit.
    - region: DDG region code — always use "wt-wt" (worldwide). Do not change this.
    """
    try:
        with DDGS() as ddgs:
            raw = ddgs.text(
                query + _EXCLUDE_SUFFIX,
                region=region,
                timelimit=timelimit,
                max_results=max_results,
                safesearch="off",
            )
            items = list(raw or [])
            if not items:
                return f"[web_search] No results found for query: {query}"
            lines = [f"[web_search] Results for: {query}"]  # show original query, not the filtered one
            for i, r in enumerate(items, 1):
                lines.append(f"\n[{i}] {r['title']}")
                lines.append(f"    URL: {r['href']}")
                lines.append(f"    Snippet: {r['body']}")
            return "\n".join(lines)
    except RatelimitException:
        return "[web_search] Error: DDG rate limit hit — retry after a short delay"
    except DuckDuckGoSearchException as e:
        return f"[web_search] Error: {e}"


async def fetch_page(url: str, max_chars: int = 4000) -> dict:
    """
    Fetch and extract the readable text content of a web page.
    Use after web_search() when a snippet is insufficient to assess relevance.
    Strips HTML, navigation, ads — returns main article text only.
    Source authority: same as web_search — lower than OTX.

    Parameters:
    - url: The URL to fetch.
    - max_chars: Truncate output to this many characters (default 4000).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15.0,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            for tag in soup(["script", "style", "nav", "footer", "header",
                              "aside", "form", "iframe", "noscript"]):
                tag.decompose()

            lines = [ln for ln in soup.get_text(separator="\n", strip=True).splitlines() if ln.strip()]
            clean_text = "\n".join(lines)[:max_chars]

            return {
                "url": url,
                "content": clean_text,
                "truncated": len(clean_text) == max_chars,
                "source": "web_fetch",
                "provider": "duckduckgo",
            }

    except httpx.TimeoutException:
        return {"url": url, "error": "Request timed out", "source": "web_fetch"}
    except httpx.HTTPStatusError as e:
        return {"url": url, "error": f"HTTP {e.response.status_code}", "source": "web_fetch"}
    except Exception as e:
        return {"url": url, "error": str(e), "source": "web_fetch"}


def register_web_search_tools(mcp):
    mcp.tool(web_search)
    mcp.tool(fetch_page)
