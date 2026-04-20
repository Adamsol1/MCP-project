"""Local uploaded-document search MCP tool."""

import csv
import json
import os
import re
from pathlib import Path

UPLOADS_ROOT = Path(
    os.getenv(
        "UPLOADS_ROOT",
        str(Path(__file__).resolve().parents[3] / "backend" / "data" / "imports"),
    )
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
    body = markdown_text[closing_idx + 5:]

    metadata: dict[str, str] = {}
    for line in header.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if key in {
            "author", "year", "title", "publisher",
            "file_upload_id", "source_filename", "session_id",
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


def _db_search_uploads(session_id: str, terms: list[str], max_results: int) -> list[dict] | None:
    """Search uploaded_files table for keyword matches. Returns None if DB unavailable."""
    try:
        from db import get_sessions_connection
        conn = get_sessions_connection()
        rows = conn.execute(
            "SELECT id, original_filename, parsed_content, citation, searchable, search_skip_reason "
            "FROM uploaded_files WHERE session_id = ? ORDER BY uploaded_at",
            (session_id,),
        ).fetchall()
        conn.close()
    except Exception:
        return None

    results: list[dict] = []
    for row in rows:
        if not row["searchable"]:
            continue
        content = row["parsed_content"] or ""
        if not content:
            continue
        score = _score_text(content, terms)
        if score <= 0:
            continue
        citation = json.loads(row["citation"]) if row["citation"] else _default_citation(row["original_filename"])
        results.append({
            "score": score,
            "file_upload_id": row["id"],
            "filename": row["original_filename"],
            "page_reference": None,
            "snippet": _make_snippet(content, terms),
            "citation": citation,
            "apa_citation": _format_apa_citation(citation),
        })

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:max_results]


def search_local_data(session_id: str, query: str, max_results: int = 20) -> str:
    """Search uploaded session files for evidence snippets and citation metadata.

    Tries sessions.db (uploaded_files table) first, falls back to manifest.json.
    """
    if not query.strip():
        raise ValueError("query cannot be empty")
    if max_results < 1:
        raise ValueError("max_results must be >= 1")

    terms = _split_query_terms(query)
    if not terms:
        raise ValueError("query must contain searchable terms")

    # Try DB first
    db_results = _db_search_uploads(session_id, terms, max_results)
    if db_results is not None:
        for item in db_results:
            item.pop("score", None)
        return json.dumps({
            "session_id": session_id,
            "query": query,
            "results": db_results,
            "total_results": len(db_results),
            "skipped": [],
        })

    # Fallback to manifest-based search
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


def register_local_search_tools(mcp) -> None:
    mcp.tool(search_local_data)
