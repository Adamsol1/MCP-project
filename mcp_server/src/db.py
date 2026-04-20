"""Lightweight sync sqlite3 access for the MCP server.

The MCP server reads knowledge.db and sessions.db (uploaded_files) in
read-only mode.  Both backends share the same .db files via WAL mode.
"""

import json
import os
import sqlite3
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATA_DIR = _PROJECT_ROOT / "backend" / "data"


def _resolve_db(env_var: str, filename: str) -> str:
    override = os.getenv(env_var)
    if override:
        return override
    return str(_DEFAULT_DATA_DIR / filename)


def get_knowledge_connection() -> sqlite3.Connection:
    """Open a read-only WAL connection to knowledge.db."""
    path = _resolve_db("KNOWLEDGE_DB_PATH", "knowledge.db")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def get_sessions_connection() -> sqlite3.Connection:
    """Open a read-only WAL connection to sessions.db (for uploaded files)."""
    path = _resolve_db("SESSIONS_DB_PATH", "sessions.db")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn
