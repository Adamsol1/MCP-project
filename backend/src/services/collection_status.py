"""CollectionStatusTracker — writes live tool-call progress to disk during collection.

The frontend polls GET /api/dialogue/collection-status/{session_id} every ~1.5 s
while isCollecting is true, reading this file to drive the live source indicator
in the IntelligencePanel.

Status file location: backend/data/collection_status/{session_id}.json
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("app")

_STATUS_DIR = Path(__file__).parent.parent.parent / "data" / "collection_status"

# Maps MCP tool names to the UI source label shown in the frontend.
_TOOL_TO_SOURCE: dict[str, str] = {
    "list_knowledge_base": "Knowledge Bank",
    "read_knowledge_base": "Knowledge Bank",
    "query_otx": "AlienVault OTX",
    "search_local_data": "Uploaded Documents",
    "list_uploads": "Uploaded Documents",
    "read_upload": "Uploaded Documents",
    "google_search": "Web Search",
    "google_news_search": "Web Search",
}

# Tools that represent a page fetch — shown as current_activity and increment the current source count.
_FETCH_TOOLS: set[str] = {"fetch_page"}


class CollectionStatusTracker:
    """Writes live per-source tool-call counts to a JSON file for frontend polling.

    Usage in collection_service.py::

        tracker = CollectionStatusTracker(session_id, selected_sources)
        # pass to GeminiAgent.run(status_tracker=tracker)
        tracker.mark_complete()
    """

    def __init__(self, session_id: str, selected_sources: list[str]) -> None:
        _STATUS_DIR.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self._path = _STATUS_DIR / f"{session_id}.json"
        self._data: dict = {
            "session_id": session_id,
            "status": "collecting",
            "current_source": None,
            "current_activity": None,
            "sources": {
                source: {"call_count": 0, "last_called_at": None}
                for source in selected_sources
            },
        }
        self._flush()

    def record_tool_call(self, tool_name: str, tool_args: dict | None = None) -> None:
        """Update the status file when the agent calls a tool."""
        if tool_name in _FETCH_TOOLS:
            # Page fetch: show as activity and count it under the current source.
            self._data["current_activity"] = "Reading page"
            current = self._data.get("current_source")
            if current and current in self._data["sources"]:
                now = datetime.now(UTC).isoformat()
                self._data["sources"][current]["call_count"] += 1
                self._data["sources"][current]["last_called_at"] = now
            self._flush()
            return
        source = _TOOL_TO_SOURCE.get(tool_name)
        if not source or source not in self._data["sources"]:
            return
        now = datetime.now(UTC).isoformat()
        self._data["sources"][source]["call_count"] += 1
        self._data["sources"][source]["last_called_at"] = now
        self._data["current_source"] = source
        self._data["current_activity"] = None
        self._flush()

    def mark_complete(self) -> None:
        """Mark the collection run as finished."""
        self._data["status"] = "complete"
        self._data["current_source"] = None
        self._data["current_activity"] = None
        self._flush()

    def _flush(self) -> None:
        try:
            self._path.write_text(json.dumps(self._data), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"[CollectionStatus] Failed to write status file: {exc}")

    @staticmethod
    def read(session_id: str) -> dict | None:
        """Read the current status for a session. Returns None if not found."""
        path = _STATUS_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
