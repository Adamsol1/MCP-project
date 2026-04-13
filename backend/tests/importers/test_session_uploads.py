import io
from pathlib import Path

import pytest

from src.importers.session_uploads import (
    default_uploads_root,
    delete_session_upload,
    format_apa_citation,
    sanitize_filename,
    save_session_upload,
    validate_session_id,
)


def _build_minimal_pdf() -> bytes:
    """Create a valid one-page PDF with extractable text."""
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    stream = io.BytesIO()
    canv = canvas.Canvas(stream)
    canv.setAuthor("Jane Analyst")
    canv.setTitle("Threat Report")
    canv.drawString(72, 720, "Sample threat intelligence content.")
    canv.save()
    return stream.getvalue()


def test_default_uploads_root_points_to_data_imports():
    root = default_uploads_root()
    assert root.name == "imports"
    assert root.parent.name == "data"


def test_pdf_upload_writes_markdown_with_required_front_matter(tmp_path):
    pytest.importorskip("pypdf")
    pdf_content = _build_minimal_pdf()
    result = save_session_upload(
        file_obj=io.BytesIO(pdf_content),
        filename="sample.pdf",
        session_id="session-a",
        uploads_root=tmp_path,
        mime_type="application/pdf",
    )

    parsed_path = Path(result["parsed_markdown_path"])
    assert parsed_path.exists()
    markdown = parsed_path.read_text(encoding="utf-8")

    assert markdown.startswith("---\n")
    assert 'file_upload_id: "' in markdown
    assert 'session_id: "session-a"' in markdown
    assert 'source_filename: "sample.pdf"' in markdown
    assert 'author: "' in markdown
    assert 'year: "' in markdown
    assert 'title: "' in markdown
    assert 'publisher: "' in markdown
    assert "ocr_applied: false" in markdown
    assert "## Page 1" in markdown


def test_pdf_missing_metadata_uses_unknown_and_flags(tmp_path):
    # Minimal fake PDF bytes intentionally fail parser/metadata extraction path.
    result = save_session_upload(
        file_obj=io.BytesIO(b"%PDF-1.4\nnot-a-real-pdf"),
        filename="broken.pdf",
        session_id="session-a",
        uploads_root=tmp_path,
        mime_type="application/pdf",
    )

    assert result["citation"]["author"] == "Unknown"
    assert result["citation"]["year"] == "Unknown"
    assert result["citation"]["publisher"] == "Unknown"
    assert result["parse_status"] in {"failed", "skipped"}
    assert result["searchable"] is False


@pytest.mark.parametrize("session_id", [
    "valid-session",
    "abc123",
    "A_B-C",
    "a" * 128,
])
def test_validate_session_id_accepts_valid_ids(session_id):
    # Arrange / Act / Assert
    assert validate_session_id(session_id) == session_id.strip()


@pytest.mark.parametrize("session_id", [
    "",
    "   ",
    "has spaces",
    "has/slash",
    "has.dot",
    "a" * 129,
])
def test_validate_session_id_rejects_invalid_ids(session_id):
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        validate_session_id(session_id)


@pytest.mark.parametrize("filename, expected_clean", [
    ("normal.txt", "normal.txt"),
    ("file with spaces.txt", "file with spaces.txt"),
    ("../../etc/passwd.txt", "passwd.txt"),
    ("file<>:*?.txt", "file_____.txt"),
])
def test_sanitize_filename_removes_dangerous_characters(filename, expected_clean):
    # Arrange / Act
    result = sanitize_filename(filename)

    # Assert
    assert result == expected_clean
    assert ".." not in result
    assert "/" not in result


def test_save_session_upload_txt_creates_manifest_entry(tmp_path):
    # Arrange
    content = b"intelligence report content"

    # Act
    result = save_session_upload(
        file_obj=io.BytesIO(content),
        filename="report.txt",
        session_id="session-txt",
        uploads_root=tmp_path,
    )

    # Assert
    assert result["filename"] == "report.txt"
    assert result["parse_status"] == "ready"
    assert result["searchable"] is True
    assert Path(result["parsed_markdown_path"]).exists()
    manifest_path = tmp_path / "session-txt" / "manifest.json"
    assert manifest_path.exists()


def test_delete_session_upload_returns_false_when_not_found(tmp_path):
    # Arrange / Act
    deleted = delete_session_upload(
        session_id="session-missing",
        file_upload_id="nonexistent-id",
        uploads_root=tmp_path,
    )

    # Assert
    assert deleted is False


def test_format_apa_citation_from_canonical_fields():
    citation = {
        "author": "Jane Analyst",
        "year": "2026",
        "title": "Threat Report",
        "publisher": "Security Org",
    }
    assert (
        format_apa_citation(citation)
        == "Jane Analyst. (2026). Threat Report. Security Org."
    )
