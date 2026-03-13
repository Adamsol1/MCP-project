"""MCP Threat Intelligence Server - Generation Server (port 8001)."""

# import asyncio  # only used by MISP (not configured on external server)
import csv
import json
import logging
import os
import re
from pathlib import Path
from sys import stderr

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import JSONResponse

# from pymisp import PyMISP  # MISP not configured on external server
from prompts import (
    build_collection_collect_prompt,
    build_collection_modify_prompt,
    build_collection_plan_prompt,
    build_collection_summarize_prompt,
    build_direction_dialogue_prompt,
    build_direction_summary_prompt,
    build_pir_generation_prompt,
)
from resources import KNOWLEDGE_REGISTRY, RESOURCES_DIR
from tools.upload_tools import register_upload_tools

load_dotenv()

print("Starting MCP Threat Intelligence Server...", file=stderr, flush=True)

mcp = FastMCP(
    name="ThreatIntelligence",
    instructions=(
        "MCP server providing OSINT tools and knowledge bank resources for the "
        "Collection and Processing phases of the Threat Intelligence cycle."
    ),
)

# Register tools from the upload_tools module to allow file uploads to the MCP staging area. These tools will be used by the Collection Agent to stage parsed markdown files for processing in the Direction phase.
register_upload_tools(mcp)


UPLOADS_ROOT = Path(
    os.getenv(
        "UPLOADS_ROOT",
        str(Path(__file__).resolve().parents[2] / "backend" / "data" / "imports"),
    )
)


# Knowledge Bank Resources


@mcp.resource("knowledge://index", mime_type="application/json")
def knowledge_index() -> str:
    """Index of all knowledge bank resources with their keywords and URIs."""
    return json.dumps(
        [
            {
                "uri": f"knowledge://{resource_id}",
                "id": resource_id,
                "keywords": entry["keywords"],
                "priority": entry["priority"],
                "citation": entry.get("citation"),
            }
            for resource_id, entry in KNOWLEDGE_REGISTRY.items()
        ]
    )


@mcp.resource("knowledge://{category}/{name}", mime_type="text/markdown")
def knowledge_resource(category: str, name: str) -> str:
    """Read a specific knowledge bank resource by category and name."""
    resource_id = f"{category}/{name}"
    if resource_id not in KNOWLEDGE_REGISTRY:
        available = list(KNOWLEDGE_REGISTRY.keys())
        raise ValueError(f"Unknown resource: '{resource_id}'. Available: {available}")

    path = RESOURCES_DIR / f"{resource_id}.md"
    if not path.exists():
        raise ValueError(f"Resource file not found: {resource_id}")

    return path.read_text(encoding="utf-8")


# Knowledge Bank Tools


@mcp.tool
def list_knowledge_base() -> str:
    """List all available knowledge bank resource IDs."""
    return json.dumps(list(KNOWLEDGE_REGISTRY.keys()))


@mcp.tool
def read_knowledge_base(resource_id: str) -> str:
    """Read a knowledge bank resource by its ID."""
    if resource_id not in KNOWLEDGE_REGISTRY:
        available = list(KNOWLEDGE_REGISTRY.keys())
        raise ValueError(
            f"Unknown resource_id: '{resource_id}'. Available: {available}"
        )

    path = RESOURCES_DIR / f"{resource_id}.md"
    if not path.exists():
        raise ValueError(f"Resource file not found: {resource_id}")

    return path.read_text(encoding="utf-8")


# Direction Prompts


@mcp.prompt
def direction_gathering(
    user_message: str,
    missing_fields: str,
    context: str,
    language: str = "en",
) -> str:
    """Prompt for generating a clarifying question in the Direction dialogue phase."""
    ctx = json.loads(context)
    return build_direction_dialogue_prompt(
        user_message=user_message,
        missing_fields=json.loads(missing_fields),
        perspectives=ctx.get("perspectives", []),
        context=ctx,
        language=language,
    )


@mcp.prompt
def direction_summary(
    scope: str,
    timeframe: str,
    target_entities: str,
    threat_actors: str,
    priority_focus: str,
    perspectives: str,
    modifications: str = "",
    language: str = "en",
) -> str:
    """Prompt for generating a context summary in the Direction phase.

    Args:
        scope: The focus area of the investigation.
        timeframe: The time period of the investigation.
        target_entities: JSON array of relevant entities.
        threat_actors: JSON array of threat actors.
        priority_focus: The main aspect to emphasize.
        perspectives: JSON array of selected perspectives.
        modifications: Optional user feedback to incorporate.
        language: BCP-47 language code.
    """
    return build_direction_summary_prompt(
        scope=scope,
        timeframe=timeframe,
        target_entities=json.loads(target_entities),
        threat_actors=json.loads(threat_actors),
        priority_focus=priority_focus,
        perspectives=json.loads(perspectives),
        modifications=modifications or None,
        language=language,
    )


@mcp.prompt
def direction_pir(
    scope: str,
    timeframe: str,
    target_entities: str,
    threat_actors: str,
    priority_focus: str,
    perspectives: str,
    modifications: str = "",
    current_pir: str = "",
    language: str = "en",
    background_knowledge: str = "",
) -> str:
    """Prompt for generating PIRs from gathered dialogue context."""
    return build_pir_generation_prompt(
        scope=scope,
        timeframe=timeframe,
        target_entities=json.loads(target_entities),
        threat_actors=json.loads(threat_actors),
        priority_focus=priority_focus,
        perspectives=json.loads(perspectives),
        modifications=modifications or None,
        current_pir=current_pir or None,
        language=language,
        background_knowledge=background_knowledge or None,
    )


# ── Collection Prompts ───────────────────────────────────────────────────────


@mcp.prompt
def collection_plan(
    pir: str,
    modifications: str = "",
    language: str = "en",
) -> str:
    """Prompt for generating a collection plan and suggesting relevant sources.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        modifications: Optional user feedback to modify an existing plan.
        language: BCP-47 language code (e.g. "en", "no").
    """
    return build_collection_plan_prompt(
        pir=pir,
        modifications=modifications or None,
        language=language,
    )


@mcp.prompt
def collection_collect(
    pir: str,
    selected_sources: str,
    plan: str,
    session_id: str = "",
    since_date: str = "",
    existing_data: str = "",
) -> str:
    """Prompt for collecting raw intelligence data via tools in the Collection phase.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        selected_sources: JSON array of source names approved by the analyst.
        plan: The approved collection plan text.
        session_id: Session ID used for search_local_data (uploaded documents).
        since_date: ISO date (YYYY-MM-DD) to filter OTX pulses by modification date.
        existing_data: Raw data already collected in previous attempts (for retry context).
    """
    return build_collection_collect_prompt(
        pir=pir,
        selected_sources=json.loads(selected_sources),
        plan=plan,
        session_id=session_id or None,
        since_date=since_date or None,
        existing_data=existing_data or None,
    )


@mcp.prompt
def collection_summarize(
    pir: str,
    collected_data: str,
    language: str = "en",
) -> str:
    """Prompt for summarizing raw collected data in the Collection phase.

    Args:
        pir: The approved PIRs from the Direction phase (JSON string).
        collected_data: Raw data JSON returned by the collection agent.
        language: BCP-47 language code (e.g. "en", "no").
    """
    return build_collection_summarize_prompt(
        pir=pir,
        collected_data=collected_data,
        language=language,
    )


@mcp.prompt
def collection_modify(
    collected_data: str,
    modifications: str,
    language: str = "en",
) -> str:
    """Prompt for applying analyst modifications to an existing collection summary.

    Args:
        collected_data: The existing collected summary (JSON string).
        modifications: The analyst's requested changes.
        language: BCP-47 language code (e.g. "en", "no").
    """
    return build_collection_modify_prompt(
        collected_data=collected_data,
        modifications=modifications,
        language=language,
    )


# OSINT Tools (Collection phase)


# ------------------------------------------------------------------
# MISP helpers — commented out: MISP not configured on external server
# ------------------------------------------------------------------

# _MISP_TYPE_MAP: dict[str, str] = {
#     "ip-dst": "ipv4",
#     "ip-src": "ipv4",
#     "ip-dst|port": "ipv4",
#     "ip-src|port": "ipv4",
#     "domain": "domain",
#     "hostname": "domain",
#     "url": "url",
#     "md5": "md5",
#     "sha1": "sha1",
#     "sha256": "sha256",
#     "filename|md5": "md5",
#     "filename|sha1": "sha1",
#     "filename|sha256": "sha256",
#     "email-src": "email",
#     "email-dst": "email",
#     "vulnerability": "cve",
# }
#
# _MISP_THREAT_LEVELS: dict[int, str] = {
#     1: "high",
#     2: "medium",
#     3: "low",
#     4: "undefined",
# }
#
# _MISP_ANALYSIS_STATUS: dict[int, str] = {
#     0: "initial",
#     1: "ongoing",
#     2: "complete",
# }
#
#
# def _get_misp_client() -> PyMISP | None:
#     """Create a PyMISP client from environment variables.
#
#     Returns None if MISP_URL or MISP_API_KEY are not set.
#     """
#     misp_url = os.getenv("MISP_URL")
#     misp_key = os.getenv("MISP_API_KEY")
#     if not misp_url or not misp_key:
#         return None
#     verify_ssl = os.getenv("MISP_VERIFY_SSL", "false").lower() == "true"
#     return PyMISP(misp_url, misp_key, ssl=verify_ssl)
#
#
# def _extract_misp_ioc_value(misp_type: str, raw_value: str) -> str:
#     """Extract the IOC value from a MISP composite attribute value."""
#     if "|" in misp_type and "|" in raw_value:
#         parts = raw_value.split("|", 1)
#         if misp_type in ("ip-dst|port", "ip-src|port"):
#             return parts[0]
#         return parts[1]
#     return raw_value
#
#
# def _normalize_misp_type(misp_type: str, value: str) -> str:
#     """Map a MISP attribute type to standardized type string."""
#     ioc_type = _MISP_TYPE_MAP.get(misp_type, misp_type)
#     if ioc_type == "ipv4" and ":" in value:
#         return "ipv6"
#     return ioc_type
#
#
# def _format_misp_indicator(attr: dict) -> dict:
#     """Format a MISP attribute dict into a standardized indicator dict."""
#     misp_type = attr.get("type", "")
#     raw_value = attr.get("value", "")
#     value = _extract_misp_ioc_value(misp_type, raw_value)
#     return {
#         "type": _normalize_misp_type(misp_type, value),
#         "value": value,
#         "category": attr.get("category", ""),
#         "comment": attr.get("comment") or "",
#         "to_ids": attr.get("to_ids", False),
#     }
#
#
# def _format_misp_event(event_data: dict) -> dict:
#     """Format a raw MISP event dict into a standardized event dict."""
#     evt = event_data.get("Event", event_data)
#
#     orgc = evt.get("Orgc", {})
#     org_name = orgc.get("name", "") if isinstance(orgc, dict) else ""
#
#     raw_tags = evt.get("Tag", [])
#     tags = [t["name"] for t in raw_tags if isinstance(t, dict) and "name" in t]
#
#     attributes = evt.get("Attribute", [])
#     indicators = [_format_misp_indicator(a) for a in attributes]
#
#     threat_level_id = int(evt.get("threat_level_id", 4))
#     analysis = int(evt.get("analysis", 0))
#
#     return {
#         "event_id": evt.get("id", ""),
#         "title": evt.get("info", ""),
#         "org_name": org_name,
#         "threat_level": _MISP_THREAT_LEVELS.get(threat_level_id, "undefined"),
#         "analysis_status": _MISP_ANALYSIS_STATUS.get(analysis, "initial"),
#         "date": evt.get("date", ""),
#         "tags": tags,
#         "indicators": indicators,
#     }
#
#
# @mcp.tool
# async def search_misp(
#     search_term: str,
#     search_type: str = "attribute",
#     date_from: str | None = None,
#     date_to: str | None = None,
#     threat_level: int | None = None,
#     distribution: int | None = None,
#     max_results: int = 50,
# ) -> str:
#     """Search a MISP instance for threat intelligence events and indicators.
#
#     Supports three search modes via search_type:
#     - "attribute": Search by IOC value (IP, domain, hash, URL, email, CVE).
#     - "tag": Search events by tag name (e.g., "tlp:green", "apt29").
#     - "event_id": Fetch a specific event by its numeric ID.
#
#     Optional filters: date range, threat level (1-4), distribution level (0-4).
#
#     Returns events in standardized format with event metadata and indicators.
#     """
#     if not search_term.strip():
#         raise ValueError("search_term cannot be empty")
#     if search_type not in ("attribute", "tag", "event_id"):
#         raise ValueError(
#             f"search_type must be 'attribute', 'tag', or 'event_id', "
#             f"got '{search_type}'"
#         )
#
#     client = _get_misp_client()
#     if client is None:
#         raise ValueError(
#             "MISP is not configured. Set MISP_URL and MISP_API_KEY "
#             "environment variables."
#         )
#
#     kwargs: dict[str, object] = {}
#     if date_from:
#         kwargs["date_from"] = date_from
#     if date_to:
#         kwargs["date_to"] = date_to
#     if threat_level is not None:
#         kwargs["threat_level_id"] = threat_level
#     if distribution is not None:
#         kwargs["distribution"] = distribution
#
#     events: list[dict] = []
#
#     if search_type == "attribute":
#         kwargs["controller"] = "attributes"
#         kwargs["value"] = search_term.strip()
#
#         response = await asyncio.to_thread(client.search, **kwargs)
#
#         if isinstance(response, dict) and "errors" in response:
#             raise ValueError(f"MISP API error: {response['errors']}")
#
#         # Attribute search returns {"Attribute": [{..., "Event": {...}}, ...]}
#         attr_list = response.get("Attribute", []) if isinstance(response, dict) else []
#
#         # Group attributes by event ID to build event-centric results
#         event_map: dict[str, dict] = {}
#         for attr in attr_list[:max_results]:
#             evt_info = attr.get("Event", {})
#             eid = evt_info.get("id", "unknown")
#             if eid not in event_map:
#                 orgc = evt_info.get("Orgc", {})
#                 org_name = orgc.get("name", "") if isinstance(orgc, dict) else ""
#                 tl = int(evt_info.get("threat_level_id", 4))
#                 an = int(evt_info.get("analysis", 0))
#                 event_map[eid] = {
#                     "event_id": eid,
#                     "title": evt_info.get("info", ""),
#                     "org_name": org_name,
#                     "threat_level": _MISP_THREAT_LEVELS.get(tl, "undefined"),
#                     "analysis_status": _MISP_ANALYSIS_STATUS.get(an, "initial"),
#                     "date": evt_info.get("date", ""),
#                     "tags": [],
#                     "indicators": [],
#                 }
#             event_map[eid]["indicators"].append(_format_misp_indicator(attr))
#
#         events = list(event_map.values())
#
#     else:
#         kwargs["controller"] = "events"
#         if search_type == "tag":
#             kwargs["tags"] = [search_term.strip()]
#         elif search_type == "event_id":
#             kwargs["eventid"] = search_term.strip()
#
#         kwargs["limit"] = max_results
#
#         response = await asyncio.to_thread(client.search, **kwargs)
#
#         if isinstance(response, dict) and "errors" in response:
#             raise ValueError(f"MISP API error: {response['errors']}")
#
#         if isinstance(response, list):
#             events = [_format_misp_event(r) for r in response[:max_results]]
#
#     return json.dumps(
#         {
#             "source": "misp",
#             "search_term": search_term,
#             "search_type": search_type,
#             "total_results": len(events),
#             "events": events,
#         }
#     )


logger = logging.getLogger("app")

OTX_BASE_URL = "https://otx.alienvault.com/api/v1"

# OTX indicator type string -> API path segment
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
    """Make an authenticated GET request to the OTX API.

    Args:
        path: API path (appended to OTX_BASE_URL).
        params: Query parameters.

    Returns:
        Parsed JSON response, or empty dict on failure.
    """
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
            raise PermissionError("OTX API key is invalid or not authorized (HTTP 403)") from e
        return {}
    except httpx.HTTPError as e:
        logger.error(f"[query_otx] Request failed: {e}")
        return {}


def _format_indicator_result(indicator: dict, pulse_name: str, tags: list[str]) -> dict:
    """Format a single indicator into the standard result shape."""
    return {
        "indicator": indicator.get("indicator", ""),
        "type": indicator.get("type", ""),
        "pulse_name": pulse_name,
        "tags": tags,
        "first_seen": indicator.get("created"),
        "last_seen": indicator.get("expiration"),
    }


def _search_otx_indicator(indicator_type: str, value: str) -> list[dict]:
    """Search OTX by indicator value (IP, domain, hash, etc.)."""
    section = _OTX_INDICATOR_SECTIONS.get(indicator_type.lower())
    if not section:
        return []

    data = _otx_request(f"indicators/{section}/{value}/general")
    if not data:
        return []

    results: list[dict] = []
    pulse_info = data.get("pulse_info", {})
    for pulse in pulse_info.get("pulses", []):
        pulse_name = pulse.get("name", "")
        tags = pulse.get("tags", [])
        # Add the queried indicator itself as a result
        results.append(
            {
                "indicator": value,
                "type": indicator_type,
                "pulse_name": pulse_name,
                "tags": tags,
                "first_seen": pulse.get("created"),
                "last_seen": pulse.get("modified"),
            }
        )

    return results


def _search_otx_pulses(query: str, since_date: str = "") -> list[dict]:
    """Search OTX pulses by keyword (adversary, malware, etc.)."""
    all_results: list[dict] = []
    limit = 10

    for page in range(1, 2):  # Single page — fetch 10 results in one request
        params: dict = {"q": query, "limit": limit, "page": page}
        if since_date:
            params["modified_since"] = since_date
        data = _otx_request(
            "search/pulses", params=params
        )
        if not data:
            break

        pulses = data.get("results", [])
        for pulse in pulses:
            pulse_name = pulse.get("name", "")
            tags = pulse.get("tags", [])
            adversary = pulse.get("adversary")
            malware_families = pulse.get("malware_families", [])

            all_results.append(
                {
                    "pulse_id": pulse.get("id", ""),
                    "indicator": adversary or query,
                    "type": "pulse",
                    "pulse_name": pulse_name,
                    "tags": tags,
                    "first_seen": pulse.get("created"),
                    "last_seen": pulse.get("modified"),
                    "adversary": adversary,
                    "malware_families": malware_families,
                    "targeted_countries": pulse.get("targeted_countries", []),
                }
            )

        if len(pulses) < limit:
            break

    return all_results


def _fetch_pulse_details(pulse_id: str) -> dict:
    """Fetch full details for a single OTX pulse by ID."""
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


@mcp.tool
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
            return json.dumps({
                "search_term": search_term,
                "indicator_type": indicator_type,
                "results": results,
                "total_results": len(results),
            })
        else:
            pulses = _search_otx_pulses(search_term.strip(), since_date=since_date.strip())
    except PermissionError as e:
        return json.dumps({"error": str(e), "search_term": search_term, "results": [], "total_results": 0})

    # Enrich top 3 pulses with full details (IoCs, TTPs, description, etc.)
    enriched = []
    for pulse in pulses[:3]:
        pulse_id = pulse.get("pulse_id", "")
        if pulse_id:
            details = _fetch_pulse_details(pulse_id)
            pulse.update(details)
        enriched.append(pulse)

    # Remaining pulses returned as metadata only
    remaining = pulses[3:]

    return json.dumps({
        "search_term": search_term,
        "indicator_type": "keyword",
        "total_results": len(pulses),
        "enriched_pulses": enriched,
        "additional_pulses": remaining,
    })


def _split_query_terms(query: str) -> list[str]:
    return [token for token in re.split(r"\s+", query.strip().lower()) if token]


def _score_text(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(term) for term in terms)


def _make_snippet(text: str, terms: list[str], width: int = 180) -> str:
    lowered = text.lower()
    indices = [lowered.find(term) for term in terms if term in lowered]
    if not indices:
        return text[:width].strip()
    start = max(min(indices) - (width // 2), 0)
    end = min(start + width, len(text))
    return text[start:end].strip()


def _default_citation(filename: str) -> dict[str, str]:
    return {
        "author": "Unknown",
        "year": "Unknown",
        "title": Path(filename).stem or "Unknown",
        "publisher": "Unknown",
    }


def _format_apa_citation(citation: dict[str, str]) -> str:
    return (
        f"{citation.get('author', 'Unknown')}. "
        f"({citation.get('year', 'Unknown')}). "
        f"{citation.get('title', 'Unknown')}. "
        f"{citation.get('publisher', 'Unknown')}."
    )


def _parse_markdown_front_matter(markdown_text: str) -> tuple[dict[str, str], str]:
    if not markdown_text.startswith("---\n"):
        return {}, markdown_text

    closing_idx = markdown_text.find("\n---\n", 4)
    if closing_idx < 0:
        return {}, markdown_text

    header = markdown_text[4:closing_idx]
    body = markdown_text[closing_idx + 5 :]

    metadata: dict[str, str] = {}
    for line in header.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key in {
            "author",
            "year",
            "title",
            "publisher",
            "file_upload_id",
            "source_filename",
            "session_id",
        }:
            metadata[key] = value
    return metadata, body


def _extract_page_sections(markdown_body: str) -> list[tuple[int, str]]:
    sections: list[tuple[int, str]] = []
    current_page: int | None = None
    buffer: list[str] = []

    for raw_line in markdown_body.splitlines():
        line = raw_line.strip()
        match = re.match(r"^## Page (\d+)$", line)
        if match:
            if current_page is not None:
                sections.append((current_page, "\n".join(buffer).strip()))
            current_page = int(match.group(1))
            buffer = []
            continue
        if current_page is not None:
            buffer.append(raw_line)

    if current_page is not None:
        sections.append((current_page, "\n".join(buffer).strip()))
    return sections


def _read_text_by_extension(path: Path, extension: str) -> str:
    if extension == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if extension == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return json.dumps(data, indent=2, ensure_ascii=False)
    if extension == ".csv":
        rows: list[str] = []
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                rows.append(" | ".join(row))
        return "\n".join(rows)
    return ""


def _search_record(entry: dict, terms: list[str], max_results: int) -> list[dict]:
    extension = str(entry.get("extension", "")).lower()
    filename = str(entry.get("filename") or entry.get("original_filename") or "unknown")
    file_upload_id = str(entry.get("file_upload_id", ""))
    citation = entry.get("citation") or _default_citation(filename)

    results: list[dict] = []

    if extension == ".pdf":
        parsed_path = entry.get("parsed_markdown_path")
        if not parsed_path:
            return []
        md_path = Path(parsed_path)
        if not md_path.exists():
            return []

        raw_markdown = md_path.read_text(encoding="utf-8", errors="ignore")
        front_matter, body = _parse_markdown_front_matter(raw_markdown)
        if front_matter:
            citation = {
                "author": front_matter.get("author", "Unknown"),
                "year": front_matter.get("year", "Unknown"),
                "title": front_matter.get("title", Path(filename).stem or "Unknown"),
                "publisher": front_matter.get("publisher", "Unknown"),
            }

        for page_number, page_text in _extract_page_sections(body):
            score = _score_text(page_text, terms)
            if score <= 0:
                continue
            results.append(
                {
                    "score": score,
                    "file_upload_id": file_upload_id,
                    "filename": filename,
                    "page_reference": f"Page {page_number}",
                    "snippet": _make_snippet(page_text, terms),
                    "citation": citation,
                    "apa_citation": _format_apa_citation(citation),
                }
            )
            if len(results) >= max_results:
                break
        return results

    stored_path = entry.get("stored_path")
    if not stored_path:
        return []

    source_path = Path(stored_path)
    if not source_path.exists():
        return []

    try:
        text = _read_text_by_extension(source_path, extension)
    except Exception:
        return []

    if not text:
        return []

    score = _score_text(text, terms)
    if score <= 0:
        return []

    return [
        {
            "score": score,
            "file_upload_id": file_upload_id,
            "filename": filename,
            "page_reference": None,
            "snippet": _make_snippet(text, terms),
            "citation": citation,
            "apa_citation": _format_apa_citation(citation),
        }
    ]


@mcp.tool
def search_local_data(session_id: str, query: str, max_results: int = 20) -> str:
    """Search uploaded session files for evidence snippets and citation metadata."""
    if not query.strip():
        raise ValueError("query cannot be empty")
    if max_results < 1:
        raise ValueError("max_results must be >= 1")

    manifest_path = UPLOADS_ROOT / session_id / "manifest.json"
    if not manifest_path.exists():
        return json.dumps(
            {
                "session_id": session_id,
                "query": query,
                "results": [],
                "total_results": 0,
                "skipped": ["manifest_not_found"],
            }
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("manifest is not valid JSON") from exc

    terms = _split_query_terms(query)
    if not terms:
        raise ValueError("query must contain searchable terms")

    combined_results: list[dict] = []
    skipped: list[str] = []
    for entry in manifest.get("files", []):
        if not entry.get("searchable", True):
            filename = str(
                entry.get("filename") or entry.get("original_filename") or "unknown"
            )
            reason = str(entry.get("search_skip_reason") or "not_searchable")
            skipped.append(f"{filename}:{reason}")
            continue

        combined_results.extend(_search_record(entry, terms, max_results))

    combined_results.sort(key=lambda item: item.get("score", 0), reverse=True)
    trimmed = combined_results[:max_results]
    for item in trimmed:
        item.pop("score", None)

    return json.dumps(
        {
            "session_id": session_id,
            "query": query,
            "results": trimmed,
            "total_results": len(trimmed),
            "skipped": skipped,
        }
    )


# Processing Tools
# TODO: Implement normalize_data, enrich_ioc, map_to_mitre


# Health check


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    print("Health check - server is running.", file=stderr, flush=True)
    return JSONResponse({"status": "ok"})


# Test tool


@mcp.tool
def greet() -> str:
    """Test tool to verify the server is running."""
    print("MCP greet() called - server is running.", file=stderr, flush=True)
    return "MCP Threat Intelligence Server is running."


if __name__ == "__main__":
    port = int(os.getenv("MCP_SERVER_PORT", "8001"))
    mcp.run(
        transport="sse",
        host="127.0.0.1",
        port=port,
        show_banner=False,
        log_level="INFO",
    )
