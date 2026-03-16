import os
import shutil
from pathlib import Path


def _default_uploads_dir() -> Path:
    # backend/src/services/mcp_staging.py → parents[3] = project root
    return Path(__file__).resolve().parents[3] / "mcp_server" / "uploads"


def get_staged_path(session_id: str, file_upload_id: str) -> Path:
    """Return the path where the file is staged in the MCP uploads directory.

    Uses MCP_UPLOADS_DIR env var when set, otherwise resolves the default
    mcp_server/uploads/ directory relative to this file's location.
    """
    uploads_dir = Path(os.getenv("MCP_UPLOADS_DIR", str(_default_uploads_dir())))
    return uploads_dir / session_id / f"{file_upload_id}.md"


def stage_to_mcp(
    session_id: str, file_upload_id: str, parsed_markdown_path: str
) -> bool:
    """Copy the parsed markdown file to the MCP staging directory.

    Target path: {uploads_dir}/{session_id}/{file_upload_id}.md
    Creates the session subdirectory if it does not exist.

    Returns True on success, False if the source file does not exist.
    """
    stages_path = get_staged_path(session_id, file_upload_id)

    if not Path(parsed_markdown_path).exists():
        return False

    stages_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(parsed_markdown_path, stages_path)
    return True


def unstage_from_mcp(session_id: str, file_upload_id: str) -> bool:
    """Remove the staged markdown file from the MCP uploads directory.

    Returns True if the file was removed, False if it did not exist.
    """
    stages_path = get_staged_path(session_id, file_upload_id)

    if not stages_path.exists():
        return False
    stages_path.unlink()
    return True


def unstage_session_from_mcp(session_id: str) -> bool:
    """Remove the entire session staging directory from the MCP uploads directory.

    Returns True if the directory was removed, False if it did not exist.
    """
    uploads_dir = Path(os.getenv("MCP_UPLOADS_DIR", str(_default_uploads_dir())))
    session_dir = uploads_dir / session_id

    if not session_dir.exists():
        return False
    shutil.rmtree(session_dir)
    return True
