from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestSessionScopedUploads:
    @pytest.mark.parametrize(
        "file_name, content",
        [
            ("test.txt", b"test data"),
            ("test.pdf", b"%PDF-1.4\n% mock"),
            ("test.json", b'{"ok":true}'),
            ("test.csv", b"a,b\n1,2\n"),
        ],
    )
    def test_upload_legal_filetype(self, file_name, content, mock_upload_path):  # noqa: ARG002
        response = client.post(
            "/api/import/upload",
            data={"session_id": "session-a"},
            files={"file": (file_name, content, "application/octet-stream")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["session_id"] == "session-a"
        assert data["file_upload_id"]
        assert data["path"]

    @pytest.mark.parametrize(
        "file_name, content",
        [
            ("test.exe", b"test data"),
            ("test.bat", b"test data"),
            ("test.sh", b"test data"),
            ("test.docx", b"test data"),
        ],
    )
    def test_upload_illegal_filetype(self, file_name, content):
        response = client.post(
            "/api/import/upload",
            data={"session_id": "session-a"},
            files={"file": (file_name, content, "application/octet-stream")},
        )
        assert response.status_code == 400

    def test_upload_without_file_returns_error(self):
        response = client.post("/api/import/upload", data={"session_id": "session-a"})
        assert response.status_code == 422

    def test_upload_without_session_returns_error(self):
        response = client.post(
            "/api/import/upload",
            files={"file": ("test.txt", b"test data", "text/plain")},
        )
        assert response.status_code == 422

    def test_uploaded_file_is_saved_in_session_directory(self, mock_upload_path):
        response = client.post(
            "/api/import/upload",
            data={"session_id": "session-a"},
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        payload = response.json()
        saved_path = Path(payload["path"])

        assert saved_path.exists()
        assert saved_path.read_bytes() == b"hello"
        assert str(mock_upload_path / "session-a" / "files") in str(saved_path)

    def test_upload_empty_file(self, _mock_upload_path):
        response = client.post(
            "/api/import/upload",
            data={"session_id": "session-a"},
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        payload = response.json()
        saved_file = Path(payload["path"])

        assert response.status_code == 200
        assert saved_file.exists()
        assert saved_file.read_bytes() == b""
        assert payload["size_bytes"] == 0

    def test_list_uploaded_files_by_session(self, mock_upload_path):  # noqa: ARG002
        client.post(
            "/api/import/upload",
            data={"session_id": "session-list"},
            files={"file": ("one.txt", b"one", "text/plain")},
        )
        response = client.get(
            "/api/import/files", params={"session_id": "session-list"}
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["session_id"] == "session-list"
        assert len(payload["files"]) == 1
        assert payload["files"][0]["filename"] == "one.txt"

    def test_list_is_session_isolated(self, mock_upload_path):  # noqa: ARG002
        client.post(
            "/api/import/upload",
            data={"session_id": "session-1"},
            files={"file": ("one.txt", b"1", "text/plain")},
        )
        client.post(
            "/api/import/upload",
            data={"session_id": "session-2"},
            files={"file": ("two.txt", b"2", "text/plain")},
        )

        response1 = client.get("/api/import/files", params={"session_id": "session-1"})
        response2 = client.get("/api/import/files", params={"session_id": "session-2"})

        assert len(response1.json()["files"]) == 1
        assert response1.json()["files"][0]["filename"] == "one.txt"
        assert len(response2.json()["files"]) == 1
        assert response2.json()["files"][0]["filename"] == "two.txt"

    def test_delete_uploaded_file(self, _mock_upload_path):
        upload_response = client.post(
            "/api/import/upload",
            data={"session_id": "session-delete"},
            files={"file": ("to-delete.txt", b"delete-me", "text/plain")},
        )
        payload = upload_response.json()
        file_upload_id = payload["file_upload_id"]
        saved_path = Path(payload["path"])
        assert saved_path.exists()

        delete_response = client.delete(
            f"/api/import/files/{file_upload_id}",
            params={"session_id": "session-delete"},
        )
        assert delete_response.status_code == 204
        assert not saved_path.exists()

    def test_delete_missing_file_returns_404(self):
        response = client.delete(
            "/api/import/files/not-found",
            params={"session_id": "session-delete"},
        )
        assert response.status_code == 404
