"""ResearchLogger — writes research/reasoning log entries to sessions.db.

Uses the sync sqlite3 module because the logger is invoked from many sync
contexts (state machines, agent callbacks). The `research_log_entries` table
holds both append-style entries (ai_generation, user_action) and the full
reasoning trace written on PIR approval.
"""

import json
import logging
import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from src.models.reasoning import ReasoningLog

logger = logging.getLogger("app")

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATA_DIR = _BACKEND_ROOT / "data"

_conn: sqlite3.Connection | None = None
_conn_lock = threading.Lock()


def _db_path() -> str:
    override = os.getenv("SESSIONS_DB_PATH")
    if override:
        return override
    _DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return str(_DEFAULT_DATA_DIR / "sessions.db")


def _get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        with _conn_lock:
            if _conn is None:
                _conn = sqlite3.connect(_db_path(), check_same_thread=False)
                _conn.execute("PRAGMA journal_mode=WAL")
                _conn.execute("PRAGMA busy_timeout=5000")
    return _conn


class ResearchLogger:
    """Persists per-session research and reasoning logs to sessions.db.

    Two entry types land in the `research_log_entries` table:
      - "ai_generation" / "user_action" — appended via create_log()
      - "reasoning_log" — full reasoning trace written via write_reasoning_log()
    """

    def __init__(self, session_id: str | None = None, log_path=None):
        # log_path is kept for backwards compatibility with existing callers;
        # it is ignored (all logs now go to DB).
        self.session_id = session_id
        # Some callers (e.g., main.py delete_session) read .log_path.parent to
        # clean up legacy files. Provide a harmless path for that.
        self.log_path = _DEFAULT_DATA_DIR / "outputs" / f"research_log_{session_id}.jsonl"

    def create_log(self, log_entry) -> None:
        """Append a single research log entry (ai_generation or user_action)."""
        if hasattr(log_entry, "model_dump"):
            payload = log_entry.model_dump(mode="json")
        elif isinstance(log_entry, dict):
            payload = log_entry
        else:
            payload = {"raw": str(log_entry)}

        entry_type = payload.get("entry_type") or payload.get("action") or "ai_generation"
        phase = payload.get("phase")
        session_id = payload.get("session_id") or self.session_id
        if not session_id:
            logger.warning("[ResearchLogger] create_log called without session_id")
            return

        try:
            conn = _get_connection()
            conn.execute(
                """INSERT INTO research_log_entries
                       (session_id, entry_type, phase, timestamp, content)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    session_id,
                    entry_type,
                    phase,
                    payload.get("timestamp") or datetime.now(UTC).isoformat(),
                    json.dumps(payload),
                ),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"[ResearchLogger] Failed to write log entry: {e}")

    def write_reasoning_log(self, reasoning_log: "ReasoningLog") -> None:
        """Persist the full reasoning trace (one row per PIR approval)."""
        try:
            conn = _get_connection()
            conn.execute(
                """INSERT INTO research_log_entries
                       (session_id, entry_type, phase, timestamp, content)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    reasoning_log.session_id,
                    "reasoning_log",
                    reasoning_log.phase,
                    datetime.now(UTC).isoformat(),
                    reasoning_log.model_dump_json(),
                ),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"[ResearchLogger] Failed to write reasoning log: {e}")
