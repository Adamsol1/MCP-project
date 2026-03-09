import io
from pathlib import Path

import pytest

from src.importers.session_uploads import (
    default_uploads_root,
    format_apa_citation,
    save_session_upload,
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
