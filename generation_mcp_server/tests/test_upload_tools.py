"""TDD tests for upload MCP tools.

Run with:
    cd mcp_server && pytest tests/test_upload_tools.py -v
"""

import json

from src.server import mcp
from src.tools import upload_tools


class TestToolRegistration:
    def test_upload_file_tool_registered(self):
        assert "upload_file" in mcp._tool_manager._tools

    def test_list_uploads_tool_registered(self):
        assert "list_uploads" in mcp._tool_manager._tools

    def test_read_upload_tool_registered(self):
        assert "read_upload" in mcp._tool_manager._tools

    def test_delete_upload_tool_registered(self):
        assert "delete_upload" in mcp._tool_manager._tools


class TestDefaultUploadsDir:
    def test_default_dir_resolves_under_mcp_server(self):
        default = upload_tools._default_uploads_dir()
        assert default.parts[-2] == "mcp_server"
        assert default.parts[-1] == "uploads"


class TestUploadFile:
    def test_upload_file_creates_file_in_session_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        upload_tools.upload_file("session-1", "file-abc", "# Report\n\nContent.")
        assert (tmp_path / "session-1" / "file-abc.md").exists()

    def test_upload_file_creates_session_dir_if_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        upload_tools.upload_file("new-session", "file-xyz", "content")
        assert (tmp_path / "new-session").is_dir()

    def test_upload_file_writes_correct_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        upload_tools.upload_file("session-1", "file-abc", "# Report\n\nContent.")
        content = (tmp_path / "session-1" / "file-abc.md").read_text(encoding="utf-8")
        assert content == "# Report\n\nContent."

    def test_upload_file_returns_ok_on_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        result = upload_tools.upload_file("session-1", "file-abc", "content")
        assert result == "ok"


class TestListUploads:
    def test_list_uploads_returns_empty_for_unknown_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        result = upload_tools.list_uploads("unknown-session")
        assert json.loads(result) == []

    def test_list_uploads_returns_files_after_staging(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        session_dir = tmp_path / "session-1"
        session_dir.mkdir()
        (session_dir / "file-abc.md").write_text("content", encoding="utf-8")

        result = json.loads(upload_tools.list_uploads("session-1"))

        assert len(result) == 1
        assert result[0]["file_id"] == "file-abc"

    def test_list_uploads_returns_size_bytes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        session_dir = tmp_path / "session-1"
        session_dir.mkdir()
        text = "hello world"
        (session_dir / "file-abc.md").write_text(text, encoding="utf-8")

        result = json.loads(upload_tools.list_uploads("session-1"))
        assert result[0]["size_bytes"] == len(text.encode("utf-8"))

    def test_list_uploads_is_session_isolated(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        (tmp_path / "session-1").mkdir()
        (tmp_path / "session-2").mkdir()
        (tmp_path / "session-1" / "file-a.md").write_text("a", encoding="utf-8")
        (tmp_path / "session-2" / "file-b.md").write_text("b", encoding="utf-8")

        result_1 = json.loads(upload_tools.list_uploads("session-1"))
        result_2 = json.loads(upload_tools.list_uploads("session-2"))

        assert len(result_1) == 1 and result_1[0]["file_id"] == "file-a"
        assert len(result_2) == 1 and result_2[0]["file_id"] == "file-b"

    def test_list_uploads_ignores_non_md_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        session_dir = tmp_path / "session-1"
        session_dir.mkdir()
        (session_dir / "file-abc.md").write_text("content", encoding="utf-8")
        (session_dir / "other.txt").write_text("ignored", encoding="utf-8")

        result = json.loads(upload_tools.list_uploads("session-1"))
        assert len(result) == 1


class TestReadUpload:
    def test_read_upload_returns_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        session_dir = tmp_path / "session-1"
        session_dir.mkdir()
        (session_dir / "file-abc.md").write_text("# Report\nContent.", encoding="utf-8")

        result = upload_tools.read_upload("session-1", "file-abc")
        assert result == "# Report\nContent."

    def test_read_upload_returns_error_for_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        (tmp_path / "session-1").mkdir()
        result = upload_tools.read_upload("session-1", "nonexistent")
        assert "error" in result.lower() or "not found" in result.lower()

    def test_read_upload_returns_error_for_unknown_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        result = upload_tools.read_upload("unknown-session", "file-abc")
        assert "error" in result.lower() or "not found" in result.lower()


class TestDeleteUpload:
    def test_delete_upload_removes_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        session_dir = tmp_path / "session-1"
        session_dir.mkdir()
        (session_dir / "file-abc.md").write_text("content", encoding="utf-8")

        upload_tools.delete_upload("session-1", "file-abc")

        assert not (session_dir / "file-abc.md").exists()

    def test_delete_upload_returns_ok_on_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        session_dir = tmp_path / "session-1"
        session_dir.mkdir()
        (session_dir / "file-abc.md").write_text("content", encoding="utf-8")

        result = upload_tools.delete_upload("session-1", "file-abc")
        assert result == "ok"

    def test_delete_upload_returns_not_found_for_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        (tmp_path / "session-1").mkdir()
        result = upload_tools.delete_upload("session-1", "nonexistent")
        assert result == "not_found"

    def test_delete_upload_returns_not_found_for_unknown_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_tools, "UPLOADS_DIR", tmp_path)
        result = upload_tools.delete_upload("unknown-session", "file-abc")
        assert result == "not_found"
