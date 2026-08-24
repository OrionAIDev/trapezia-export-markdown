"""Tests for trapezia_export_markdown — run with: pytest tests/"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from trapezia_export_markdown import ExportError, export, export_dir
from trapezia_export_markdown._impl import _html_embed_flag, _parse_pandoc_version

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
# 3. HTML self-contained flag depends on pandoc version
#    Regression: --embed-resources only exists in pandoc >= 2.19. Debian bookworm
#    ships 2.17.1.1, where the equivalent flag is --self-contained. Choosing the
#    wrong flag makes `--to html` fail with "Unknown option --embed-resources".
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "version_output, expected",
    [
        ("pandoc 2.17.1.1\nCompiled with pandoc-types 1.22", (2, 17, 1, 1)),
        ("pandoc 2.19\n", (2, 19)),
        ("pandoc 2.19.2", (2, 19, 2)),
        ("pandoc 3.1.11\nFeatures ...", (3, 1, 11)),
        ("pandoc.exe 3.1.11\n", (3, 1, 11)),
    ],
)
def test_parse_pandoc_version(version_output: str, expected: tuple) -> None:
    assert _parse_pandoc_version(version_output) == expected


def test_parse_pandoc_version_unparseable_returns_zero() -> None:
    # Unknown/garbage output must not crash; treated as "very old" so the
    # broadly-compatible --self-contained flag is chosen.
    assert _parse_pandoc_version("not pandoc output at all") == (0,)


@pytest.mark.parametrize(
    "version, expected_flag",
    [
        ((2, 17, 1, 1), "--self-contained"),  # bookworm — the failing case
        ((2, 18), "--self-contained"),
        ((2, 19), "--embed-resources"),  # flag introduced here
        ((2, 19, 2), "--embed-resources"),
        ((3, 1, 11), "--embed-resources"),
        ((0,), "--self-contained"),  # unknown version → safe fallback
    ],
)
def test_html_embed_flag(version: tuple, expected_flag: str) -> None:
    assert _html_embed_flag(version) == expected_flag


# ──────────────────────────────────────────────────────────────────────────────
# 3b. HTML basic
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


# ──────────────────────────────────────────────────────────────────────────────
# 9. DOCX reference-doc (template) styling — ported from export-docs-skill
# ──────────────────────────────────────────────────────────────────────────────
@requires_pandoc
def test_export_docx_with_reference_doc(sample_md: Path, tmp_path: Path) -> None:
    # A reference doc is itself just a .docx; generate one to use as the template.
    ref = tmp_path / "template.docx"
    export(source=sample_md, to="docx", output=ref, quiet=True)

    out = tmp_path / "styled.docx"
    result = export(
        source=sample_md, to="docx", output=out, reference_doc=ref, quiet=True
    )
    assert result == out.resolve()
    assert out.is_file()
    assert out.read_bytes()[:4] == b"PK\x03\x04"


def test_reference_doc_with_non_docx_format_raises(sample_md: Path, tmp_path: Path) -> None:
    ref = tmp_path / "template.docx"
    ref.write_bytes(b"PK\x03\x04stub")
    with pytest.raises(ExportError, match="reference_doc"):
        export(
            source=sample_md, to="pdf", output=tmp_path / "x.pdf",
            reference_doc=ref, quiet=True,
        )


def test_reference_doc_missing_file_raises(sample_md: Path, tmp_path: Path) -> None:
    with pytest.raises(ExportError, match="not found"):
        export(
            source=sample_md, to="docx", output=tmp_path / "x.docx",
            reference_doc=tmp_path / "nope.docx", quiet=True,
        )


# ──────────────────────────────────────────────────────────────────────────────
# 10. export_dir — batch / whole-folder conversion (ported from export-docs-skill)
# ──────────────────────────────────────────────────────────────────────────────
def _write_md(p: Path, body: str = "# Doc\n\nbody\n") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


@requires_pandoc
def test_export_dir_basic(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    _write_md(src / "a.md")
    _write_md(src / "b.md")

    results = export_dir(src, to="html", quiet=True)

    assert len(results) == 2
    # default output dir is <source_dir>/export
    assert {r.parent for r in results} == {(src / "export").resolve()}
    assert {r.name for r in results} == {"a.html", "b.html"}
    assert all(r.is_file() for r in results)


@requires_pandoc
def test_export_dir_custom_output_dir(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    _write_md(src / "a.md")
    out_dir = tmp_path / "rendered"

    results = export_dir(src, to="html", output_dir=out_dir, quiet=True)

    assert len(results) == 1
    assert results[0] == (out_dir / "a.html").resolve()
    assert results[0].is_file()


def test_export_dir_no_markdown_raises(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ExportError, match="No markdown"):
        export_dir(empty, to="html", quiet=True)


def test_export_dir_missing_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(ExportError, match="directory"):
        export_dir(tmp_path / "nope", to="html", quiet=True)


@requires_pandoc
def test_export_dir_recursive(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    _write_md(src / "top.md")
    _write_md(src / "sub" / "deep.md")

    flat = export_dir(src, to="html", output_dir=tmp_path / "flat", quiet=True)
    assert {r.name for r in flat} == {"top.html"}

    deep = export_dir(
        src, to="html", output_dir=tmp_path / "deep", recursive=True, quiet=True
    )
    assert {r.name for r in deep} == {"top.html", "deep.html"}
