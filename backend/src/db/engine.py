"""Database engine factory for sessions.db and knowledge.db.

Both engines use WAL mode and a 5-second busy timeout so the backend
(async writer) and MCP server (sync reader) can coexist safely.
"""

import os
import threading
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

# ---------------------------------------------------------------------------
# Default DB directory: <backend>/data/
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATA_DIR = _BACKEND_ROOT / "data"

_lock = threading.RLock()


def _db_path(env_var: str, filename: str) -> Path:
    """Resolve a DB file path from an env var or the default data dir."""
    override = os.getenv(env_var)
    if override:
        return Path(override)
    _DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_DATA_DIR / filename


def _set_pragmas(dbapi_connection, _connection_record):
    """Enable WAL mode and a 5 s busy timeout on every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


# ---------------------------------------------------------------------------
# Sessions engine (thread-safe lazy singleton)
# ---------------------------------------------------------------------------
_sessions_engine = None
_sessions_session_factory = None


def get_sessions_engine():
    global _sessions_engine
    if _sessions_engine is None:
        with _lock:
            if _sessions_engine is None:
                db = _db_path("SESSIONS_DB_PATH", "sessions.db")
                engine = create_async_engine(
                    f"sqlite+aiosqlite:///{db}",
                    echo=False,
                    connect_args={"check_same_thread": False},
                )
                event.listen(engine.sync_engine, "connect", _set_pragmas)
                _sessions_engine = engine
    return _sessions_engine


def get_sessions_session_factory():
    global _sessions_session_factory
    if _sessions_session_factory is None:
        with _lock:
            if _sessions_session_factory is None:
                engine = get_sessions_engine()
                _sessions_session_factory = sessionmaker(
                    engine, class_=SQLModelAsyncSession, expire_on_commit=False
                )
    return _sessions_session_factory


# ---------------------------------------------------------------------------
# Knowledge engine (thread-safe lazy singleton)
# ---------------------------------------------------------------------------
_knowledge_engine = None
_knowledge_session_factory = None


def get_knowledge_engine():
    global _knowledge_engine
    if _knowledge_engine is None:
        with _lock:
            if _knowledge_engine is None:
                db = _db_path("KNOWLEDGE_DB_PATH", "knowledge.db")
                engine = create_async_engine(
                    f"sqlite+aiosqlite:///{db}",
                    echo=False,
                    connect_args={"check_same_thread": False},
                )
                event.listen(engine.sync_engine, "connect", _set_pragmas)
                _knowledge_engine = engine
    return _knowledge_engine


def get_knowledge_session_factory():
    global _knowledge_session_factory
    if _knowledge_session_factory is None:
        with _lock:
            if _knowledge_session_factory is None:
                engine = get_knowledge_engine()
                _knowledge_session_factory = sessionmaker(
                    engine, class_=SQLModelAsyncSession, expire_on_commit=False
                )
    return _knowledge_session_factory


# ---------------------------------------------------------------------------
# Sync DB path helpers (for MCP server / CollectionStatusTracker)
# ---------------------------------------------------------------------------


def get_sessions_db_path() -> Path:
    return _db_path("SESSIONS_DB_PATH", "sessions.db")


def get_knowledge_db_path() -> Path:
    return _db_path("KNOWLEDGE_DB_PATH", "knowledge.db")
