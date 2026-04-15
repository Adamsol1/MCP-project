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
    "list_knowledge_base": "Internal Knowledge Bank",
    "read_knowledge_base": "Internal Knowledge Bank",
    "query_otx": "AlienVault OTX",
    "search_local_data": "Uploaded Documents",
    "list_uploads": "Uploaded Documents",
    "read_upload": "Uploaded Documents",
    "google_search": "Web Search",
    "google_news_search": "Web Search",
}

# Tools that represent a secondary fetch action (shown as current_activity, not a new source).
_FETCH_TOOLS: set[str] = {"fetch_page"}

# Tools whose result count is determined by the num_results argument rather than being 1 per call.
_RESULT_COUNT_TOOLS: set[str] = {"google_search", "google_news_search"}


class CollectionStatusTracker:
    """Writes live per-source tool-call counts to a JSON file for frontend polling.

    Usage in collection_service.py::

        tracker = CollectionStatusTracker(session_id, selected_sources)
        # pass to ToolCallingAgent.run(status_tracker=tracker)
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
            # Page fetch: show as activity under the current source, don't change source or count.
            self._data["current_activity"] = "Reading page"
            self._flush()
            return
        source = _TOOL_TO_SOURCE.get(tool_name)
        if not source or source not in self._data["sources"]:
            return
        # For search tools, count by num_results arg (default 5); otherwise count 1 per call.
        if tool_name in _RESULT_COUNT_TOOLS:
            count = int((tool_args or {}).get("num_results", 5))
        else:
            count = 1
        now = datetime.now(UTC).isoformat()
        self._data["sources"][source]["call_count"] += count
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
