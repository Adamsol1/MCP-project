"""Tests for knowledge bank list/read tools."""

import json
import sqlite3
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from src.tools.knowledge_tools import (
    _db_list_ids,
    _db_read,
    _db_index,
    list_knowledge_base,
    read_knowledge_base,
    register_knowledge_tools,
)
from src.server import mcp


def _make_mock_db(rows: list[tuple] | None = None) -> types.ModuleType:
    """Return a fake 'db' module backed by an in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE knowledge_resources "
        "(id TEXT, keywords TEXT, priority INTEGER, markdown_content TEXT, citation TEXT)"
    )
    for row in rows or []:
        conn.execute("INSERT INTO knowledge_resources VALUES (?,?,?,?,?)", row)
    conn.commit()

    mock_db = types.ModuleType("db")
    mock_db.get_knowledge_connection = lambda: conn
    return mock_db


class TestDbFunctions:
    def test_db_list_ids_returns_ids_from_db(self, monkeypatch):
        # arrange
        mock_db = _make_mock_db([
            ("geopolitical/norway_russia", '["norway"]', 1, "content", None),
            ("sectors/energy", '["energy"]', 2, "content", None),
        ])
        monkeypatch.setitem(sys.modules, "db", mock_db)

        # act
        result = _db_list_ids()

        # assert
        assert result == ["geopolitical/norway_russia", "sectors/energy"]

    def test_db_read_returns_content_for_known_id(self, monkeypatch):
        # arrange
        mock_db = _make_mock_db([
            ("geopolitical/norway_russia", '[]', 1, "# Norway Russia Content", None),
        ])
        monkeypatch.setitem(sys.modules, "db", mock_db)

        # act
        result = _db_read("geopolitical/norway_russia")

        # assert
        assert result == "# Norway Russia Content"

    def test_db_read_returns_none_for_unknown_id(self, monkeypatch):
        # arrange
        mock_db = _make_mock_db([])
        monkeypatch.setitem(sys.modules, "db", mock_db)

        # act
        result = _db_read("does/not/exist")

        # assert
        assert result is None

    def test_db_index_returns_structured_entries(self, monkeypatch):
        # arrange
        citation = json.dumps({"author": "Test", "year": "2025", "title": "T", "publisher": "P"})
        mock_db = _make_mock_db([
            ("sectors/energy", '["energy", "oil"]', 2, "content", citation),
        ])
        monkeypatch.setitem(sys.modules, "db", mock_db)

        # act
        result = _db_index()

        # assert
        assert result is not None
        assert len(result) == 1
        assert result[0]["id"] == "sectors/energy"
        assert result[0]["uri"] == "knowledge://sectors/energy"
        assert "energy" in result[0]["keywords"]

    def test_list_knowledge_base_uses_db_when_available(self, monkeypatch):
        # arrange
        mock_db = _make_mock_db([
            ("sectors/energy", '["energy"]', 2, "content", None),
        ])
        monkeypatch.setitem(sys.modules, "db", mock_db)

        # act
        result = json.loads(list_knowledge_base())

        # assert
        assert result == ["sectors/energy"]


class TestListKnowledgeBase:
    def test_falls_back_to_registry_when_db_unavailable(self, monkeypatch):
        # arrange
        monkeypatch.setattr("src.tools.knowledge_tools._db_list_ids", lambda: None)

        # act
        result = json.loads(list_knowledge_base())

        # assert
        assert isinstance(result, list)
        assert len(result) > 0
        assert "geopolitical/norway_russia" in result

    def test_returns_db_ids_when_db_available(self, monkeypatch):
        # arrange
        monkeypatch.setattr(
            "src.tools.knowledge_tools._db_list_ids",
            lambda: ["geopolitical/norway_russia", "sectors/energy"],
        )

        # act
        result = json.loads(list_knowledge_base())

        # assert
        assert result == ["geopolitical/norway_russia", "sectors/energy"]


class TestReadKnowledgeBase:
    @pytest.mark.asyncio
    async def test_raises_for_unknown_resource_when_db_unavailable(self, monkeypatch):
        # arrange
        monkeypatch.setattr("src.tools.knowledge_tools._db_read", lambda _: None)

        # act / assert
        with pytest.raises(ValueError, match="Unknown resource_id"):
            await read_knowledge_base(MagicMock(), "unknown/resource", "session-1")

    @pytest.mark.asyncio
    async def test_raises_when_resource_file_not_found(self, monkeypatch, tmp_path):
        # arrange
        monkeypatch.setattr("src.tools.knowledge_tools._db_read", lambda _: None)
        monkeypatch.setattr("src.tools.knowledge_tools.RESOURCES_DIR", tmp_path)

        # act / assert
        with pytest.raises(ValueError, match="not found"):
            await read_knowledge_base(MagicMock(), "geopolitical/norway_russia", "session-1")

    @pytest.mark.asyncio
    async def test_returns_content_from_db_when_available(self, monkeypatch):
        # arrange
        monkeypatch.setattr(
            "src.tools.knowledge_tools._db_read",
            lambda _: "# Norway-Russia Relations\nContent here.",
        )

        # act
        result = await read_knowledge_base(MagicMock(), "geopolitical/norway_russia", "session-1")

        # assert
        assert "Norway-Russia Relations" in result

    @pytest.mark.asyncio
    async def test_returns_file_content_when_db_unavailable(self, monkeypatch, tmp_path):
        # arrange
        monkeypatch.setattr("src.tools.knowledge_tools._db_read", lambda _: None)
        monkeypatch.setattr("src.tools.knowledge_tools.RESOURCES_DIR", tmp_path)

        resource_path = tmp_path / "geopolitical" / "norway_russia.md"
        resource_path.parent.mkdir(parents=True)
        resource_path.write_text("# Norway-Russia test content", encoding="utf-8")

        # act
        result = await read_knowledge_base(MagicMock(), "geopolitical/norway_russia", "session-1")

        # assert
        assert "Norway-Russia test content" in result


class TestToolRegistration:
    def test_knowledge_tools_registered_on_server(self):
        # arrange / act / assert
        assert "list_knowledge_base" in mcp._tool_manager._tools
        assert "read_knowledge_base" in mcp._tool_manager._tools

    def test_register_knowledge_tools_calls_mcp_tool(self):
        # arrange
        registered = []

        class FakeMCP:
            def tool(self, fn):
                registered.append(fn.__name__)

        # act
        register_knowledge_tools(FakeMCP())

        # assert
        assert set(registered) == {"list_knowledge_base", "read_knowledge_base"}
