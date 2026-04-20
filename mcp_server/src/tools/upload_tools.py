"""Upload file management MCP tools.

Reads uploaded file metadata and parsed content from sessions.db
(uploaded_files table). Falls back to file-based staging if DB is unavailable.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("mcp_server")


def _default_uploads_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "uploads"


UPLOADS_DIR: Path = Path(os.getenv("MCP_UPLOADS_DIR", str(_default_uploads_dir())))


def _db_list(session_id: str) -> str | None:
    """List uploads from DB. Returns JSON string or None if DB unavailable."""
    try:
        from db import get_sessions_connection
        conn = get_sessions_connection()
        rows = conn.execute(
            "SELECT id, original_filename, size_bytes FROM uploaded_files WHERE session_id = ? ORDER BY uploaded_at",
            (session_id,),
        ).fetchall()
        conn.close()
        return json.dumps([
            {"file_id": r["id"], "filename": r["original_filename"], "size_bytes": r["size_bytes"]}
            for r in rows
        ])
    except Exception:
        return None


def _db_read(session_id: str, file_upload_id: str) -> str | None:
    """Read parsed content from DB. Returns content or None if unavailable."""
    try:
        from db import get_sessions_connection
        conn = get_sessions_connection()
        row = conn.execute(
            "SELECT parsed_content, original_filename FROM uploaded_files WHERE id = ? AND session_id = ?",
            (file_upload_id, session_id),
        ).fetchone()
        conn.close()
        if row and row["parsed_content"]:
            return row["parsed_content"]
    except Exception:
        pass
    return None


def upload_file(
    session_id: str, file_upload_id: str, content: str, filename: str = ""
) -> str:
    """Stage markdown content into the MCP resources/uploads directory.

    Creates {UPLOADS_DIR}/{session_id}/{filename_stem}.md, using the original
    filename stem when provided, otherwise falling back to file_upload_id.
    Returns "ok" on success.
    """
    stem = Path(filename).stem if filename else file_upload_id
    stages_path = UPLOADS_DIR / session_id / f"{stem}.md"
    stages_path.parent.mkdir(parents=True, exist_ok=True)
    stages_path.write_text(content, encoding="utf-8")
    return "ok"


def list_uploads(session_id: str) -> str:
    """List all uploaded files for a session.

    Tries sessions.db first, falls back to filesystem staging directory.
    Returns a JSON array of objects with keys: file_id, size_bytes.
    """
    db_result = _db_list(session_id)
    if db_result is not None:
        return db_result

    # Fallback to filesystem
    session_dir = UPLOADS_DIR / session_id
    if not session_dir.exists() or not session_dir.is_dir():
        return json.dumps([])

    results = []
    for file in session_dir.iterdir():
        if file.is_file() and file.suffix == ".md":
            results.append({"file_id": file.stem, "size_bytes": file.stat().st_size})

    return json.dumps(results)


def read_upload(session_id: str, file_upload_id: str) -> str:
    """Read the parsed content of an uploaded file.

    Tries sessions.db first, falls back to filesystem staging directory.
    Returns the file content, or an error string if not found.
    """
    db_content = _db_read(session_id, file_upload_id)
    if db_content is not None:
        return db_content

    # Fallback to filesystem
    file_path = UPLOADS_DIR / session_id / f"{file_upload_id}.md"
    if not file_path.exists() or not file_path.is_file():
        return "error: file not found"

    return file_path.read_text(encoding="utf-8")


def delete_upload(session_id: str, file_upload_id: str) -> str:
    """Remove a staged upload file from the MCP uploads directory.

    Returns "ok" if removed, "not_found" if the file did not exist.
    """
    file_path = UPLOADS_DIR / session_id / f"{file_upload_id}.md"

    if not file_path.exists() or not file_path.is_file():
        return "not_found"

    file_path.unlink()
    return "ok"


def register_upload_tools(mcp):
    mcp.tool(upload_file)
    mcp.tool(list_uploads)
    mcp.tool(read_upload)
    mcp.tool(delete_upload)
