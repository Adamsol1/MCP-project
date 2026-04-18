"""Repository for the collection_status table.

Uses **sync** sqlite3 because CollectionStatusTracker is called from
synchronous Gemini agent callbacks.  WAL mode permits this sync writer
to coexist with the async readers in the backend.

Uses a module-level persistent connection to avoid per-call overhead.
"""

import json
import logging
import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("app")

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
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
                _conn.row_factory = sqlite3.Row
    return _conn


class CollectionStatusRepository:
    """Sync repository for collection status — used inside agent callbacks."""

    def upsert(self, session_id: str, data: dict) -> None:
        conn = _get_connection()
        conn.execute(
            """INSERT INTO collection_status
                   (session_id, status, current_source, current_activity, sources, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                   status=excluded.status,
                   current_source=excluded.current_source,
                   current_activity=excluded.current_activity,
                   sources=excluded.sources,
                   updated_at=excluded.updated_at
            """,
            (
                session_id,
                data.get("status", "collecting"),
                data.get("current_source"),
                data.get("current_activity"),
                json.dumps(data.get("sources", {})),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()

    def get(self, session_id: str) -> dict | None:
        conn = _get_connection()
        row = conn.execute(
            "SELECT * FROM collection_status WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "session_id": row["session_id"],
            "status": row["status"],
            "current_source": row["current_source"],
            "current_activity": row["current_activity"],
            "sources": json.loads(row["sources"]),
            "updated_at": row["updated_at"],
        }

    def delete(self, session_id: str) -> None:
        conn = _get_connection()
        conn.execute(
            "DELETE FROM collection_status WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()
