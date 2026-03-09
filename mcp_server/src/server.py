"""MCP Threat Intelligence Server - Generation Server (port 8001)."""

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

from prompts import (
    build_direction_dialogue_prompt,
    build_pir_generation_prompt,
    build_summary_prompt,
)
from resources import KNOWLEDGE_REGISTRY, RESOURCES_DIR

load_dotenv()

print("Starting MCP Threat Intelligence Server...", file=stderr, flush=True)

mcp = FastMCP(
    name="ThreatIntelligence",
    instructions=(
        "MCP server providing OSINT tools and knowledge bank resources for the "
        "Collection and Processing phases of the Threat Intelligence cycle."
    ),
)

UPLOADS_ROOT = Path(
    os.getenv(
        "UPLOADS_ROOT",
        str(Path(__file__).resolve().parents[2] / "data" / "imports"),
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
    """Prompt for generating a context summary in the Direction phase."""
    return build_summary_prompt(
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


# OSINT Tools (Collection phase)
# TODO: Implement search_misp

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


def _search_otx_pulses(query: str) -> list[dict]:
    """Search OTX pulses by keyword (adversary, malware, etc.)."""
    all_results: list[dict] = []
    limit = 50

    for page in range(1, 6):  # Max 5 pages
        data = _otx_request(
            "search/pulses", params={"q": query, "limit": limit, "page": page}
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


@mcp.tool
def query_otx(search_term: str, indicator_type: str = "") -> str:
    """Query AlienVault OTX for threat intelligence on indicators or keywords.

    When indicator_type is provided (ipv4, domain, md5, sha256, etc.),
    searches for that specific indicator. Otherwise, searches OTX pulses
    by keyword (e.g., adversary name, malware family, campaign name).

    Returns a JSON list of results with indicator value, type, pulse name,
    tags, first_seen, and last_seen.
    """
    if not search_term.strip():
        raise ValueError("search_term cannot be empty")

    if indicator_type:
        results = _search_otx_indicator(indicator_type.strip(), search_term.strip())
    else:
        results = _search_otx_pulses(search_term.strip())

    return json.dumps(
        {
            "search_term": search_term,
            "indicator_type": indicator_type or "keyword",
            "results": results,
            "total_results": len(results),
        }
    )


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
