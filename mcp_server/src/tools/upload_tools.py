import json
import os
from pathlib import Path


def _default_uploads_dir() -> Path:
    # mcp_server/src/tools/upload_tools.py → parents[2] = mcp_server root
    return Path(__file__).resolve().parents[1] / "resources" / "uploads"


# Module-level staging directory. Tests can monkeypatch this attribute directly.
# Uses MCP_UPLOADS_DIR env var when set, otherwise the default mcp_server/src/resources/uploads/.
UPLOADS_DIR: Path = Path(os.getenv("MCP_UPLOADS_DIR", str(_default_uploads_dir())))


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
    """List all staged upload files for a session.

    Returns a JSON array of objects with keys: file_id, size_bytes.
    Returns an empty JSON array if the session directory does not exist.
    """
    session_dir = UPLOADS_DIR / session_id

    if not session_dir.exists() or not session_dir.is_dir():
        return json.dumps([])

    results = []
    for file in session_dir.iterdir():
        if file.is_file() and file.suffix == ".md":
            results.append({"file_id": file.stem, "size_bytes": file.stat().st_size})

    return json.dumps(results)


def read_upload(session_id: str, file_upload_id: str) -> str:
    """Read the markdown content of a staged upload file.

    Returns the file content, or an error string if the file is not found.
    """
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
