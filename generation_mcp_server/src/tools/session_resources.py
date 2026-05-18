"""Session data MCP resources.

Exposes per-session artifacts (collected data, processed findings) as MCP Resources
so the backend can fetch them via read_resource() instead of reading disk directly.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SESSIONS_DATA_DIR = Path(__file__).resolve().parents[3] / "backend" / "data" / "sessions"


def _read_processed(session_id: str) -> str | None:
    """Return the latest raw_result for a session from sessions.db, falling back to disk."""
    try:
        from db import get_sessions_connection
        conn = get_sessions_connection()
        row = conn.execute(
            "SELECT raw_result FROM processing_attempts"
            " WHERE session_id = ? ORDER BY attempt_number DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        conn.close()
        if row:
            return row["raw_result"]
    except Exception:
        logger.exception("[SessionResources] DB read failed for %s, falling back to disk", session_id)

    path = _SESSIONS_DATA_DIR / session_id / "processed.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        attempts = data.get("attempts", [])
        return attempts[-1] if attempts else None
    except Exception:
        logger.exception("[SessionResources] Failed to read processed.json for %s", session_id)
        return None


def register_session_resources(mcp) -> None:
    """Register the per-session processed-findings resource on the MCP server."""
    @mcp.resource("session://{session_id}/processed", mime_type="application/json")
    def get_processed_findings(session_id: str) -> str:
        """Latest processed findings for a session.

        Returns the raw JSON string from the last processing attempt.
        Consumed by the analysis agent to generate an AnalysisDraft.

        Args:
            session_id: The session identifier.
        """
        result = _read_processed(session_id)
        if result is None:
            logger.warning("[SessionResources] No processed data found for session %s", session_id)
            return json.dumps({"findings": [], "gaps": []})
        return result
