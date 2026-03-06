"""Session-scoped file upload storage and PDF parsing utilities."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALLOWED_FILETYPES = {".txt", ".pdf", ".json", ".csv"}
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def default_uploads_root() -> Path:
    """Return default uploads root shared between backend and MCP server."""
    return Path(__file__).resolve().parents[3] / "data" / "imports"


def legal_file_upload(filename: str) -> bool:
    """Return True when filename extension is in the allowlist."""
    return Path(filename).suffix.lower() in ALLOWED_FILETYPES


def validate_session_id(session_id: str) -> str:
    """Validate and normalize session id used as directory key."""
    normalized = session_id.strip()
    if not normalized:
        raise ValueError("session_id cannot be empty")
    if not SESSION_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "session_id contains illegal characters (allowed: a-z, A-Z, 0-9, _, -)"
        )
    return normalized


def sanitize_filename(filename: str) -> str:
    """Sanitize untrusted filenames while preserving extension."""
    base = Path(filename).name.strip()
    if not base:
        raise ValueError("filename cannot be empty")
    sanitized = re.sub(r"[^A-Za-z0-9._ -]", "_", base)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    if sanitized in {"", ".", ".."}:
        raise ValueError("filename is invalid after sanitization")
    return sanitized


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _session_paths(root: Path, session_id: str) -> dict[str, Path]:
    session_dir = root / session_id
    return {
        "session_dir": session_dir,
        "files_dir": session_dir / "files",
        "parsed_dir": session_dir / "parsed",
        "manifest_path": session_dir / "manifest.json",
    }


def _load_manifest(manifest_path: Path, session_id: str) -> dict[str, Any]:
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"manifest is not valid JSON: {manifest_path}") from exc
        if not isinstance(data, dict):
            raise ValueError("manifest root must be an object")
        data.setdefault("session_id", session_id)
        data.setdefault("created_at", _now_iso())
        data.setdefault("updated_at", _now_iso())
        data.setdefault("files", [])
        if not isinstance(data["files"], list):
            raise ValueError("manifest.files must be an array")
        return data
    now = _now_iso()
    return {
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
        "files": [],
    }


def _write_manifest(manifest_path: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = _now_iso()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = manifest_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp_path.replace(manifest_path)


def _stream_to_disk(file_obj, destination: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total_size = 0
    with destination.open("wb") as out_file:
        while True:
            chunk = file_obj.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            total_size += len(chunk)
            out_file.write(chunk)
    return digest.hexdigest(), total_size


def _extract_year(value: Any) -> str:
    if value is None:
        return "Unknown"
    if isinstance(value, datetime):
        return str(value.year)
    year_match = re.search(r"(19|20)\d{2}", str(value))
    return year_match.group(0) if year_match else "Unknown"


def _yaml_quote(value: Any) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _compose_pdf_markdown(
    *,
    file_upload_id: str,
    session_id: str,
    source_filename: str,
    citation: dict[str, str],
    metadata_confidence: str,
    metadata_flags: list[str],
    parsed_at: str,
    page_count: int,
    page_texts: list[str],
) -> str:
    lines: list[str] = [
        "---",
        f"file_upload_id: {_yaml_quote(file_upload_id)}",
        f"session_id: {_yaml_quote(session_id)}",
        f"source_filename: {_yaml_quote(source_filename)}",
        f"author: {_yaml_quote(citation['author'])}",
        f"year: {_yaml_quote(citation['year'])}",
        f"title: {_yaml_quote(citation['title'])}",
        f"publisher: {_yaml_quote(citation['publisher'])}",
        f"metadata_confidence: {_yaml_quote(metadata_confidence)}",
        "metadata_flags:",
    ]
    if metadata_flags:
        for flag in metadata_flags:
            lines.append(f"  - {_yaml_quote(flag)}")
    else:
        lines.append('  - "none"')
    lines.extend(
        [
            f"parsed_at: {_yaml_quote(parsed_at)}",
            f"page_count: {page_count}",
            "ocr_applied: false",
            "---",
            "",
            f"# {citation['title'] if citation['title'] != 'Unknown' else source_filename}",
            "",
        ]
    )

    for idx, text in enumerate(page_texts, start=1):
        lines.append(f"## Page {idx}")
        lines.append(text or "[No extractable text on this page.]")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _parse_pdf_to_markdown(
    *,
    file_upload_id: str,
    session_id: str,
    source_filename: str,
    stored_pdf_path: Path,
    parsed_path: Path,
) -> tuple[dict[str, str], str, bool, str | None, list[str]]:
    """Parse copyable PDF text and write markdown artifact.

    Returns:
        tuple of (citation, parse_status, searchable, skip_reason, metadata_flags)
    """
    try:
        from pypdf import PdfReader  # Imported lazily to avoid hard runtime import failures
    except Exception:
        citation = {
            "author": "Unknown",
            "year": "Unknown",
            "title": Path(source_filename).stem or "Unknown",
            "publisher": "Unknown",
        }
        return citation, "failed", False, "pypdf_not_available", ["pypdf_not_available"]

    try:
        reader = PdfReader(str(stored_pdf_path))
    except Exception:
        citation = {
            "author": "Unknown",
            "year": "Unknown",
            "title": Path(source_filename).stem or "Unknown",
            "publisher": "Unknown",
        }
        return citation, "failed", False, "pdf_read_failed", ["pdf_read_failed"]

    metadata = reader.metadata
    title = getattr(metadata, "title", None) if metadata else None
    author = getattr(metadata, "author", None) if metadata else None
    creation_date = getattr(metadata, "creation_date", None) if metadata else None
    producer = getattr(metadata, "producer", None) if metadata else None
    creator = getattr(metadata, "creator", None) if metadata else None

    citation = {
        "author": str(author).strip() if author else "Unknown",
        "year": _extract_year(creation_date),
        "title": str(title).strip() if title else (Path(source_filename).stem or "Unknown"),
        "publisher": (str(producer).strip() if producer else "")
        or (str(creator).strip() if creator else "")
        or "Unknown",
    }

    metadata_flags: list[str] = []
    if citation["author"] == "Unknown":
        metadata_flags.append("missing_author")
    if citation["year"] == "Unknown":
        metadata_flags.append("missing_year")
    if citation["title"] == "Unknown":
        metadata_flags.append("missing_title")
    if citation["publisher"] == "Unknown":
        metadata_flags.append("missing_publisher")

    page_texts: list[str] = []
    has_extractable_text = False
    for page in reader.pages:
        extracted = (page.extract_text() or "").strip()
        if extracted:
            has_extractable_text = True
        page_texts.append(extracted)

    if not has_extractable_text:
        metadata_flags.append("no_extractable_text")

    if not metadata_flags:
        metadata_confidence = "high"
    elif "no_extractable_text" in metadata_flags:
        metadata_confidence = "low"
    else:
        metadata_confidence = "medium"

    parsed_content = _compose_pdf_markdown(
        file_upload_id=file_upload_id,
        session_id=session_id,
        source_filename=source_filename,
        citation=citation,
        metadata_confidence=metadata_confidence,
        metadata_flags=metadata_flags,
        parsed_at=_now_iso(),
        page_count=len(page_texts),
        page_texts=page_texts,
    )
    parsed_path.parent.mkdir(parents=True, exist_ok=True)
    parsed_path.write_text(parsed_content, encoding="utf-8")

    if has_extractable_text:
        return citation, "ready", True, None, metadata_flags
    return citation, "skipped", False, "no_extractable_text", metadata_flags


def format_apa_citation(citation: dict[str, str]) -> str:
    """Format simple APA-like citation string from canonical citation fields."""
    return (
        f"{citation.get('author', 'Unknown')}. "
        f"({citation.get('year', 'Unknown')}). "
        f"{citation.get('title', 'Unknown')}. "
        f"{citation.get('publisher', 'Unknown')}."
    )


def save_session_upload(
    *,
    file_obj,
    filename: str,
    session_id: str,
    uploads_root: Path,
    mime_type: str | None = None,
) -> dict[str, Any]:
    """Save uploaded file under a session and update manifest metadata."""
    validated_session_id = validate_session_id(session_id)
    if not legal_file_upload(filename):
        raise ValueError("Illegal filetype")

    safe_filename = sanitize_filename(filename)
    extension = Path(safe_filename).suffix.lower()
    file_upload_id = str(uuid.uuid4())

    paths = _session_paths(uploads_root, validated_session_id)
    paths["files_dir"].mkdir(parents=True, exist_ok=True)
    stored_filename = f"{file_upload_id}__{safe_filename}"
    stored_path = paths["files_dir"] / stored_filename

    sha256, size_bytes = _stream_to_disk(file_obj, stored_path)
    uploaded_at = _now_iso()

    entry: dict[str, Any] = {
        "file_upload_id": file_upload_id,
        "session_id": validated_session_id,
        "original_filename": filename,
        "filename": safe_filename,
        "stored_filename": stored_filename,
        "stored_path": stored_path.as_posix(),
        "path": stored_path.as_posix(),
        "extension": extension,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "uploaded_at": uploaded_at,
        "parse_status": "ready",
        "searchable": True,
        "search_skip_reason": None,
        "parsed_markdown_path": None,
        "citation": {
            "author": "Unknown",
            "year": "Unknown",
            "title": Path(safe_filename).stem or "Unknown",
            "publisher": "Unknown",
        },
    }

    if extension == ".pdf":
        parsed_path = paths["parsed_dir"] / f"{file_upload_id}.md"
        citation, parse_status, searchable, skip_reason, metadata_flags = (
            _parse_pdf_to_markdown(
                file_upload_id=file_upload_id,
                session_id=validated_session_id,
                source_filename=safe_filename,
                stored_pdf_path=stored_path,
                parsed_path=parsed_path,
            )
        )
        entry["parse_status"] = parse_status
        entry["searchable"] = searchable
        entry["search_skip_reason"] = skip_reason
        entry["citation"] = citation
        entry["parsed_markdown_path"] = parsed_path.as_posix()
        entry["metadata_flags"] = metadata_flags

    manifest = _load_manifest(paths["manifest_path"], validated_session_id)
    manifest["files"].append(entry)
    _write_manifest(paths["manifest_path"], manifest)
    return entry


def list_session_uploads(*, session_id: str, uploads_root: Path) -> list[dict[str, Any]]:
    """List uploads for a given session."""
    validated_session_id = validate_session_id(session_id)
    manifest_path = _session_paths(uploads_root, validated_session_id)["manifest_path"]
    manifest = _load_manifest(manifest_path, validated_session_id)
    return manifest.get("files", [])


def delete_session_upload(
    *,
    session_id: str,
    file_upload_id: str,
    uploads_root: Path,
) -> bool:
    """Delete one upload and related artifacts. Returns False if not found."""
    validated_session_id = validate_session_id(session_id)
    paths = _session_paths(uploads_root, validated_session_id)
    manifest = _load_manifest(paths["manifest_path"], validated_session_id)

    kept: list[dict[str, Any]] = []
    removed_entry: dict[str, Any] | None = None
    for entry in manifest.get("files", []):
        if entry.get("file_upload_id") == file_upload_id:
            removed_entry = entry
        else:
            kept.append(entry)

    if removed_entry is None:
        return False

    for path_key in ("stored_path", "parsed_markdown_path"):
        value = removed_entry.get(path_key)
        if not value:
            continue
        target = Path(value)
        if target.exists():
            target.unlink()

    manifest["files"] = kept
    _write_manifest(paths["manifest_path"], manifest)
    return True
