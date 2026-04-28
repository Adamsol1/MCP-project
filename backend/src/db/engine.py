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


def seed_knowledge() -> None:
    """Seed knowledge.db from .md files and perspective docs. Safe to call on every startup (upsert)."""
    import sys
    sys.path.insert(0, str(_BACKEND_ROOT))
    from scripts.seed_knowledge import seed as seed_kb
    from scripts.seed_perspective_docs import seed as seed_pdocs
    seed_kb()
    seed_pdocs()


def _has_pending_migrations(cfg, db_url: str) -> bool:
    """Return True if the DB is behind the current migration head."""
    import sqlalchemy as sa
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(cfg)
    heads = set(script.get_heads())
    try:
        engine = sa.create_engine(db_url)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current = set(context.get_current_heads())
    except Exception:
        return True
    return heads != current


def run_migrations() -> bool:
    """Run alembic upgrade head for both DBs. Returns True if any new migrations were applied."""
    from alembic import command
    from alembic.config import Config

    applied = False
    for ini_name, db_path in (
        ("alembic_sessions.ini", get_sessions_db_path()),
        ("alembic_knowledge.ini", get_knowledge_db_path()),
    ):
        cfg = Config(str(_BACKEND_ROOT / ini_name))
        db_url = f"sqlite:///{db_path}"
        cfg.set_main_option("sqlalchemy.url", db_url)
        if _has_pending_migrations(cfg, db_url):
            command.upgrade(cfg, "head")
            applied = True
    return applied
