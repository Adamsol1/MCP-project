"""Tests for session data MCP resources."""

import json

from src.tools import session_resources


class TestReadProcessed:
    def test_returns_none_when_file_does_not_exist(self, tmp_path, monkeypatch):
        # arrange — point sessions dir at tmp_path (no files created)
        monkeypatch.setattr(session_resources, "_SESSIONS_DATA_DIR", tmp_path)

        # act
        result = session_resources._read_processed("nonexistent-session-abc123")

        # assert
        assert result is None

    def test_returns_last_attempt_from_file(self, tmp_path, monkeypatch):
        # arrange — use a session id that won't exist in real DB
        monkeypatch.setattr(session_resources, "_SESSIONS_DATA_DIR", tmp_path)

        session_dir = tmp_path / "test-session-file-fallback"
        session_dir.mkdir()
        first = '{"findings": [], "gaps": []}'
        last = '{"findings": [{"id": "F-001"}], "gaps": []}'
        (session_dir / "processed.json").write_text(
            json.dumps({"attempts": [first, last]}), encoding="utf-8"
        )

        # act — DB returns no row for this session, fallback reads the file
        result = session_resources._read_processed("test-session-file-fallback")

        # assert
        assert result == last

    def test_returns_none_when_attempts_list_is_empty(self, tmp_path, monkeypatch):
        # arrange
        monkeypatch.setattr(session_resources, "_SESSIONS_DATA_DIR", tmp_path)

        session_dir = tmp_path / "test-session-empty-attempts"
        session_dir.mkdir()
        (session_dir / "processed.json").write_text(
            json.dumps({"attempts": []}), encoding="utf-8"
        )

        # act
        result = session_resources._read_processed("test-session-empty-attempts")

        # assert
        assert result is None
