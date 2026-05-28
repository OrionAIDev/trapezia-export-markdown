"""Tests for trapezia_export_markdown — run with: pytest tests/"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from trapezia_export_markdown import export, ExportError


HAVE_PANDOC = shutil.which("pandoc") is not None
HAVE_PDF_ENGINE = (
    shutil.which("wkhtmltopdf") is not None
    or shutil.which("weasyprint") is not None
)
try:
    import pypdf  # noqa: F401
    HAVE_PYPDF = True
except ImportError:
    HAVE_PYPDF = False

requires_pandoc = pytest.mark.skipif(not HAVE_PANDOC, reason="pandoc not installed")
requires_pdf = pytest.mark.skipif(
    not (HAVE_PANDOC and HAVE_PDF_ENGINE),
    reason="pandoc + a PDF engine required",
)
requires_pypdf = pytest.mark.skipif(not HAVE_PYPDF, reason="pypdf not installed")


@pytest.fixture
def sample_md(tmp_path: Path) -> Path:
    p = tmp_path / "sample.md"
    p.write_text(
        "# Hello\n\nworld\n\n## Section\n\nSome body text with a "
        "[link](https://example.com).\n",
        encoding="utf-8",
    )
    return p


def _make_minimal_pdf(path: Path) -> None:
    """Generate a tiny valid PDF using pypdf for embed tests."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as f:
        writer.write(f)


# ──────────────────────────────────────────────────────────────────────────────
# 1. PDF basic
# ──────────────────────────────────────────────────────────────────────────────
@requires_pdf
def test_export_pdf_basic(sample_md: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.pdf"
    result = export(source=sample_md, to="pdf", output=out, quiet=True)
    assert result == out.resolve()
    assert out.is_file()
    assert out.stat().st_size > 0
    if HAVE_PYPDF:
        from pypdf import PdfReader
        reader = PdfReader(str(out))
        assert len(reader.pages) >= 1


# ──────────────────────────────────────────────────────────────────────────────
# 2. DOCX basic
# ──────────────────────────────────────────────────────────────────────────────
@requires_pandoc
def test_export_docx_basic(sample_md: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.docx"
    export(source=sample_md, to="docx", output=out, quiet=True)
    assert out.is_file()
    assert out.stat().st_size > 0
    # docx files are zip archives — first bytes are PK\x03\x04
    assert out.read_bytes()[:4] == b"PK\x03\x04"


# ──────────────────────────────────────────────────────────────────────────────
# 3. HTML basic
# ──────────────────────────────────────────────────────────────────────────────
@requires_pandoc
def test_export_html_basic(sample_md: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.html"
    export(source=sample_md, to="html", output=out, quiet=True)
    assert out.is_file()
    content = out.read_text(encoding="utf-8")
    assert "<h1" in content and "Hello" in content
    assert "world" in content


# ──────────────────────────────────────────────────────────────────────────────
# 4. PDF + embed-pdfs concatenation
# ──────────────────────────────────────────────────────────────────────────────
@requires_pdf
@requires_pypdf
def test_export_pdf_with_embed_pdfs(sample_md: Path, tmp_path: Path) -> None:
    raw1 = tmp_path / "raw1.pdf"
    raw2 = tmp_path / "raw2.pdf"
    _make_minimal_pdf(raw1)
    _make_minimal_pdf(raw2)

    out = tmp_path / "packet.pdf"
    export(
        source=sample_md,
        to="pdf",
        output=out,
        embed_pdfs=[raw1, raw2],
        quiet=True,
    )

    from pypdf import PdfReader
    reader = PdfReader(str(out))
    assert len(reader.pages) >= 3  # main(>=1) + raw1(1) + raw2(1)

    # Bookmarks (outlines) should include our embed filenames
    outline_titles: list[str] = []

    def _walk(items):
        for item in items:
            if isinstance(item, list):
                _walk(item)
            else:
                t = getattr(item, "title", None)
                if t:
                    outline_titles.append(t)

    _walk(reader.outline)
    joined = " ".join(outline_titles)
    assert "raw1.pdf" in joined
    assert "raw2.pdf" in joined


# ──────────────────────────────────────────────────────────────────────────────
# 5. Title extraction from H1
# ──────────────────────────────────────────────────────────────────────────────
@requires_pandoc
def test_export_title_extraction_from_h1(tmp_path: Path) -> None:
    src = tmp_path / "doc.md"
    src.write_text("# My Document\n\nBody.\n", encoding="utf-8")
    out = tmp_path / "out.html"
    export(source=src, to="html", output=out, quiet=True)
    content = out.read_text(encoding="utf-8")
    assert "<title>My Document</title>" in content


# ──────────────────────────────────────────────────────────────────────────────
# 6. Explicit title overrides H1
# ──────────────────────────────────────────────────────────────────────────────
@requires_pandoc
def test_export_explicit_title_overrides_h1(tmp_path: Path) -> None:
    src = tmp_path / "doc.md"
    src.write_text("# Wrong\n\nBody.\n", encoding="utf-8")
    out = tmp_path / "out.html"
    export(source=src, to="html", output=out, title="Right", quiet=True)
    content = out.read_text(encoding="utf-8")
    assert "<title>Right</title>" in content
    assert "<title>Wrong</title>" not in content


# ──────────────────────────────────────────────────────────────────────────────
# 7. Invalid format raises
# ──────────────────────────────────────────────────────────────────────────────
def test_export_invalid_format_raises(sample_md: Path, tmp_path: Path) -> None:
    with pytest.raises(ExportError):
        export(source=sample_md, to="docx2", output=tmp_path / "x", quiet=True)


# ──────────────────────────────────────────────────────────────────────────────
# 8. Missing source raises before pandoc invocation
# ──────────────────────────────────────────────────────────────────────────────
def test_export_missing_source_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "does_not_exist.md"
    with pytest.raises(ExportError, match="not found"):
        export(source=bogus, to="html", output=tmp_path / "x.html", quiet=True)
