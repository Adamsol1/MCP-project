"""AlienVault OTX MCP tool."""

import json
import logging
import os

import httpx

logger = logging.getLogger("app")

OTX_BASE_URL = "https://otx.alienvault.com/api/v1"

_OTX_INDICATOR_SECTIONS: dict[str, str] = {
    "ipv4": "IPv4",
    "ipv6": "IPv6",
    "domain": "domain",
    "url": "url",
    "md5": "file",
    "sha1": "file",
    "sha256": "file",
    "email": "email",
    "cve": "cve",
}


def _otx_request(path: str, params: dict | None = None) -> dict:
    api_key = os.getenv("OTX_API_KEY")
    if not api_key:
        logger.error("[query_otx] OTX_API_KEY environment variable is not set")
        return {}

    url = f"{OTX_BASE_URL}/{path.lstrip('/')}"
    headers = {"X-OTX-API-KEY": api_key}

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"[query_otx] HTTP {e.response.status_code} for {path}")
        if e.response.status_code == 403:
            raise PermissionError(
                "OTX API key is invalid or not authorized (HTTP 403)"
            ) from e
        return {}
    except httpx.HTTPError as e:
        logger.error(f"[query_otx] Request failed: {e}")
        return {}


def _search_otx_indicator(indicator_type: str, value: str) -> list[dict]:
    section = _OTX_INDICATOR_SECTIONS.get(indicator_type.lower())
    if not section:
        return []

    data = _otx_request(f"indicators/{section}/{value}/general")
    if not data:
        return []

    results: list[dict] = []
    pulse_info = data.get("pulse_info", {})
    for pulse in pulse_info.get("pulses", []):
        results.append(
            {
                "indicator": value,
                "type": indicator_type,
                "pulse_name": pulse.get("name", ""),
                "tags": pulse.get("tags", []),
                "first_seen": pulse.get("created"),
                "last_seen": pulse.get("modified"),
            }
        )

    return results


def _search_otx_pulses(query: str, since_date: str = "") -> list[dict]:
    all_results: list[dict] = []
    limit = 10

    for page in range(1, 2):  # Single page — fetch 10 results in one request
        params: dict = {"q": query, "limit": limit, "page": page}
        if since_date:
            params["modified_since"] = since_date
        data = _otx_request("search/pulses", params=params)
        if not data:
            break

        pulses = data.get("results", [])
        for pulse in pulses:
            all_results.append(
                {
                    "pulse_id": pulse.get("id", ""),
                    "indicator": pulse.get("adversary") or query,
                    "type": "pulse",
                    "pulse_name": pulse.get("name", ""),
                    "tags": pulse.get("tags", []),
                    "first_seen": pulse.get("created"),
                    "last_seen": pulse.get("modified"),
                    "adversary": pulse.get("adversary"),
                    "malware_families": pulse.get("malware_families", []),
                    "targeted_countries": pulse.get("targeted_countries", []),
                }
            )

        if len(pulses) < limit:
            break

    return all_results


def _fetch_pulse_details(pulse_id: str) -> dict:
    data = _otx_request(f"pulses/{pulse_id.strip()}")
    if not data:
        return {"pulse_id": pulse_id, "error": "No data returned"}
    indicators = data.get("indicators", [])
    return {
        "pulse_id": pulse_id,
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "adversary": data.get("adversary", ""),
        "malware_families": data.get("malware_families", []),
        "targeted_countries": data.get("targeted_countries", []),
        "tags": data.get("tags", []),
        "created": data.get("created", ""),
        "modified": data.get("modified", ""),
        "references": data.get("references", []),
        "indicators": [
            {
                "indicator": ind.get("indicator", ""),
                "type": ind.get("type", ""),
                "description": ind.get("description", ""),
            }
            for ind in indicators[:50]
        ],
        "indicator_count": len(indicators),
    }


def query_otx(search_term: str, indicator_type: str = "", since_date: str = "") -> str:
    """Query AlienVault OTX for threat intelligence on indicators or keywords.

    When indicator_type is provided (ipv4, domain, md5, sha256, etc.),
    searches for that specific indicator. Otherwise, searches OTX pulses
    by keyword (e.g., adversary name, malware family, campaign name) and
    automatically fetches full details (IoCs, TTPs, description, targeted
    countries, references) for the top 3 matching pulses.

    Use since_date (YYYY-MM-DD) to filter pulses modified after a given date.
    """
    if not search_term.strip():
        raise ValueError("search_term cannot be empty")

    try:
        if indicator_type:
            results = _search_otx_indicator(indicator_type.strip(), search_term.strip())
            return json.dumps(
                {
                    "search_term": search_term,
                    "indicator_type": indicator_type,
                    "results": results,
                    "total_results": len(results),
                }
            )
        else:
            pulses = _search_otx_pulses(search_term.strip(), since_date=since_date.strip())
    except PermissionError as e:
        return json.dumps(
            {
                "error": str(e),
                "search_term": search_term,
                "results": [],
                "total_results": 0,
            }
        )

    enriched = []
    for pulse in pulses[:3]:
        pulse_id = pulse.get("pulse_id", "")
        if pulse_id:
            details = _fetch_pulse_details(pulse_id)
            pulse.update(details)
        enriched.append(pulse)

    return json.dumps(
        {
            "search_term": search_term,
            "indicator_type": "keyword",
            "total_results": len(pulses),
            "enriched_pulses": enriched,
            "additional_pulses": pulses[3:],
        }
    )


def register_otx_tools(mcp) -> None:
    mcp.tool(query_otx)
