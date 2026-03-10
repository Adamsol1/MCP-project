"""TDD tests for mcp_staging service.

Run with:
    cd backend && pytest tests/services/test_mcp_staging.py -v
"""

from pathlib import Path

import pytest

from src.services import mcp_staging


class TestGetStagedPath:
    def test_returns_correct_path_when_env_set(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MCP_UPLOADS_DIR", str(tmp_path))
        result = mcp_staging.get_staged_path("session-1", "file-abc")
        assert result == tmp_path / "session-1" / "file-abc.md"

    def test_returns_default_path_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("MCP_UPLOADS_DIR", raising=False)
        result = mcp_staging.get_staged_path("session-1", "file-abc")
        assert "mcp_server" in result.parts
        assert "uploads" in result.parts
        assert result.name == "file-abc.md"

    def test_includes_md_extension(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MCP_UPLOADS_DIR", str(tmp_path))
        result = mcp_staging.get_staged_path("s", "f")
        assert result.suffix == ".md"


class TestStageToMcp:
    def test_stage_copies_markdown_to_mcp_dir(self, tmp_path, monkeypatch):
        mcp_dir = tmp_path / "mcp_uploads"
        monkeypatch.setenv("MCP_UPLOADS_DIR", str(mcp_dir))

        source = tmp_path / "file-abc.md"
        source.write_text("# Intelligence Report\n\nSome content.", encoding="utf-8")

        mcp_staging.stage_to_mcp("session-1", "file-abc", str(source))

        staged = mcp_dir / "session-1" / "file-abc.md"
        assert staged.read_text(encoding="utf-8") == "# Intelligence Report\n\nSome content."

    def test_stage_creates_session_subdir_if_missing(self, tmp_path, monkeypatch):
        mcp_dir = tmp_path / "mcp_uploads"
        monkeypatch.setenv("MCP_UPLOADS_DIR", str(mcp_dir))

        source = tmp_path / "file-abc.md"
        source.write_text("content", encoding="utf-8")

        mcp_staging.stage_to_mcp("new-session", "file-abc", str(source))

        assert (mcp_dir / "new-session").is_dir()

    def test_stage_returns_true_on_success(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MCP_UPLOADS_DIR", str(tmp_path))

        source = tmp_path / "file-abc.md"
        source.write_text("content", encoding="utf-8")

        result = mcp_staging.stage_to_mcp("session-1", "file-abc", str(source))
        assert result is True

    def test_stage_returns_false_if_source_does_not_exist(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MCP_UPLOADS_DIR", str(tmp_path))
        result = mcp_staging.stage_to_mcp("session-1", "file-abc", str(tmp_path / "nonexistent.md"))
        assert result is False

    def test_stage_does_not_modify_source_file(self, tmp_path, monkeypatch):
        mcp_dir = tmp_path / "mcp_uploads"
        monkeypatch.setenv("MCP_UPLOADS_DIR", str(mcp_dir))

        source = tmp_path / "file-abc.md"
        source.write_text("original content", encoding="utf-8")

        mcp_staging.stage_to_mcp("session-1", "file-abc", str(source))

        assert source.read_text(encoding="utf-8") == "original content"


class TestUnstageFromMcp:
    def test_unstage_removes_file(self, tmp_path, monkeypatch):
        mcp_dir = tmp_path / "mcp_uploads"
        staged = mcp_dir / "session-1" / "file-abc.md"
        staged.parent.mkdir(parents=True)
        staged.write_text("content", encoding="utf-8")
        monkeypatch.setenv("MCP_UPLOADS_DIR", str(mcp_dir))

        mcp_staging.unstage_from_mcp("session-1", "file-abc")

        assert not staged.exists()

    def test_unstage_returns_true_if_removed(self, tmp_path, monkeypatch):
        mcp_dir = tmp_path / "mcp_uploads"
        staged = mcp_dir / "session-1" / "file-abc.md"
        staged.parent.mkdir(parents=True)
        staged.write_text("content", encoding="utf-8")
        monkeypatch.setenv("MCP_UPLOADS_DIR", str(mcp_dir))

        result = mcp_staging.unstage_from_mcp("session-1", "file-abc")
        assert result is True

    def test_unstage_returns_false_if_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MCP_UPLOADS_DIR", str(tmp_path))
        result = mcp_staging.unstage_from_mcp("session-1", "nonexistent")
        assert result is False
