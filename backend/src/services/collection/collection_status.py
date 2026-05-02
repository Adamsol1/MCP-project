"""CollectionStatusTracker — writes live tool-call progress to sessions.db during collection.

The frontend polls GET /api/dialogue/collection-status/{session_id} every ~1.5 s
while isCollecting is true, reading from the collection_status table to drive
the live source indicator in the IntelligencePanel.

Uses the sync CollectionStatusRepository because this tracker is invoked from
synchronous Gemini agent callbacks.
"""

import logging
from datetime import UTC, datetime

from src.db.repositories.collection_status_repo import CollectionStatusRepository

logger = logging.getLogger("app")

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

# Tools that are lookup/search operations and should not increment the result count.
# google_search/google_news_search are included here because their num_results reflects raw URL
# candidates, not summarized pages. The real Web Search count is set after the second pass via
# set_source_count().
_NO_COUNT_TOOLS: set[str] = {
    "list_uploads",
    "search_local_data",
    "google_search",
    "google_news_search",
}

_repo = CollectionStatusRepository()


class CollectionStatusTracker:
    """Writes live per-source tool-call counts to collection_status table for frontend polling.

    Usage in collection_service.py::

        tracker = CollectionStatusTracker(session_id, selected_sources)
        # pass to GeminiAgent.run(status_tracker=tracker)
        tracker.mark_complete()
    """

    def __init__(self, session_id: str, selected_sources: list[str]) -> None:
        self.session_id = session_id
        self._read_file_ids: set[str] = set()
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
        """Update the status row when the agent calls a tool."""
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
        self._data["current_source"] = source
        self._data["current_activity"] = None
        now = datetime.now(UTC).isoformat()
        self._data["sources"][source]["last_called_at"] = now
        # Lookup/search tools update current_source for live feedback but don't count as results.
        if tool_name in _NO_COUNT_TOOLS:
            self._flush()
            return
        if tool_name == "read_upload":
            # Count each unique file once, not each call.
            file_id = (tool_args or {}).get("file_upload_id", "")
            if file_id in self._read_file_ids:
                self._flush()
                return
            self._read_file_ids.add(file_id)
            count = 1
        else:
            count = 1
        self._data["sources"][source]["call_count"] += count
        self._flush()

    def set_source_count(self, source: str, count: int) -> None:
        """Overwrite the result count for a source (used after post-processing passes)."""
        if source in self._data["sources"]:
            self._data["sources"][source]["call_count"] = count
            self._flush()

    def mark_complete(self) -> None:
        """Mark the collection run as finished."""
        self._data["status"] = "complete"
        self._data["current_source"] = None
        self._data["current_activity"] = None
        self._flush()

    def _flush(self) -> None:
        try:
            _repo.upsert(self.session_id, self._data)
        except Exception as exc:
            logger.warning(f"[CollectionStatus] Failed to upsert status: {exc}")

    @staticmethod
    def read(session_id: str) -> dict | None:
        """Read the current status for a session. Returns None if not found."""
        try:
            return _repo.get(session_id)
        except Exception:
            return None
