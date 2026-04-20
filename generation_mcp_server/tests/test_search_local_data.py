import json
from pathlib import Path

from src import server


def _write_session_manifest(root: Path, session_id: str, files: list[dict]) -> None:
    session_dir = root / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "session_id": session_id,
        "created_at": "2026-03-06T00:00:00Z",
        "updated_at": "2026-03-06T00:00:00Z",
        "files": files,
    }
    (session_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_search_local_data_finds_text_file(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "UPLOADS_ROOT", tmp_path)

    text_path = tmp_path / "s1" / "files" / "file1__intel.txt"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text("APT29 targeted Norwegian infrastructure", encoding="utf-8")

    _write_session_manifest(
        tmp_path,
        "s1",
        [
            {
                "file_upload_id": "file1",
                "filename": "intel.txt",
                "stored_path": text_path.as_posix(),
                "extension": ".txt",
                "searchable": True,
            }
        ],
    )

    raw = server.search_local_data.fn("s1", "apt29 norwegian")
    data = json.loads(raw)

    assert data["total_results"] == 1
    assert data["results"][0]["file_upload_id"] == "file1"
    assert "apt29" in data["results"][0]["snippet"].lower()


def test_search_local_data_finds_pdf_markdown_with_page_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "UPLOADS_ROOT", tmp_path)

    parsed_path = tmp_path / "s1" / "parsed" / "pdf1.md"
    parsed_path.parent.mkdir(parents=True, exist_ok=True)
    parsed_path.write_text(
        "\n".join(
            [
                "---",
                'file_upload_id: "pdf1"',
                'session_id: "s1"',
                'source_filename: "report.pdf"',
                'author: "Jane Analyst"',
                'year: "2026"',
                'title: "Threat Report"',
                'publisher: "Security Org"',
                "---",
                "",
                "# Threat Report",
                "",
                "## Page 1",
                "No useful content here.",
                "",
                "## Page 2",
                "APT29 campaign details and norwegian targets.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    _write_session_manifest(
        tmp_path,
        "s1",
        [
            {
                "file_upload_id": "pdf1",
                "filename": "report.pdf",
                "extension": ".pdf",
                "searchable": True,
                "parsed_markdown_path": parsed_path.as_posix(),
            }
        ],
    )

    raw = server.search_local_data.fn("s1", "norwegian")
    data = json.loads(raw)

    assert data["total_results"] == 1
    result = data["results"][0]
    assert result["page_reference"] == "Page 2"
    assert result["citation"]["author"] == "Jane Analyst"
    assert result["apa_citation"] == "Jane Analyst. (2026). Threat Report. Security Org."


def test_search_local_data_is_session_isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "UPLOADS_ROOT", tmp_path)

    file_a = tmp_path / "s1" / "files" / "a.txt"
    file_a.parent.mkdir(parents=True, exist_ok=True)
    file_a.write_text("keyword alpha", encoding="utf-8")
    _write_session_manifest(
        tmp_path,
        "s1",
        [
            {
                "file_upload_id": "a",
                "filename": "a.txt",
                "stored_path": file_a.as_posix(),
                "extension": ".txt",
                "searchable": True,
            }
        ],
    )

    file_b = tmp_path / "s2" / "files" / "b.txt"
    file_b.parent.mkdir(parents=True, exist_ok=True)
    file_b.write_text("keyword beta", encoding="utf-8")
    _write_session_manifest(
        tmp_path,
        "s2",
        [
            {
                "file_upload_id": "b",
                "filename": "b.txt",
                "stored_path": file_b.as_posix(),
                "extension": ".txt",
                "searchable": True,
            }
        ],
    )

    data_s1 = json.loads(server.search_local_data.fn("s1", "beta"))
    data_s2 = json.loads(server.search_local_data.fn("s2", "beta"))

    assert data_s1["total_results"] == 0
    assert data_s2["total_results"] == 1
