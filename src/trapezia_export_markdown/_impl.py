"""Core implementation of trapezia_export_markdown.

Converts markdown files to PDF, DOCX, or HTML via pandoc + (wkhtmltopdf or
weasyprint). Supports appending raw PDFs after the main content via pypdf.

Public API:
    from trapezia_export_markdown import export, ExportError

System dependencies (NOT pip-installable):
    - pandoc            (apt-get install pandoc) — required, all formats
    - wkhtmltopdf       (apt-get install wkhtmltopdf) — for PDF (preferred)
    - weasyprint        (apt-get install weasyprint) — for PDF (fallback)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Optional, Sequence

__all__ = ["export", "ExportError", "DEFAULT_CSS"]

VALID_FORMATS = {"pdf", "docx", "html"}
VALID_PAGE_SIZES = {"letter", "a4"}

# Clean clinical default style — serif body, sans headings, generous margins
DEFAULT_CSS = """
@page {
    size: __PAGE_SIZE__;
    margin: 1in;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-family: Helvetica, Arial, sans-serif;
        font-size: 9pt;
        color: #666;
    }
}
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #222;
    max-width: 7.5in;
    margin: 0 auto;
}
h1, h2, h3, h4, h5, h6 {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    color: #1a3a5c;
    margin-top: 1.2em;
    margin-bottom: 0.4em;
    line-height: 1.2;
}
h1 {
    font-size: 22pt;
    border-bottom: 2px solid #1a3a5c;
    padding-bottom: 0.25em;
    page-break-before: always;
}
h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 16pt; color: #2a5a85; }
h3 { font-size: 13pt; color: #3a6a95; }
p  { margin: 0.5em 0; }
ul, ol { margin: 0.5em 0 0.5em 1.5em; }
li { margin: 0.2em 0; }
code {
    font-family: "Menlo", "Consolas", monospace;
    background: #f4f4f4;
    padding: 0.1em 0.3em;
    border-radius: 3px;
    font-size: 90%;
}
pre {
    background: #f4f4f4;
    padding: 0.8em;
    border-left: 3px solid #1a3a5c;
    overflow-x: auto;
    font-size: 90%;
}
pre code { background: none; padding: 0; }
blockquote {
    border-left: 3px solid #999;
    padding-left: 1em;
    color: #555;
    margin: 1em 0;
}
table {
    border-collapse: collapse;
    margin: 1em 0;
    width: 100%;
}
th, td {
    border: 1px solid #ccc;
    padding: 0.4em 0.6em;
    text-align: left;
}
th {
    background: #eaeef3;
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
}
a { color: #1a5aa5; text-decoration: none; }
a:hover { text-decoration: underline; }
#TOC, nav#TOC {
    background: #f8f8f8;
    border: 1px solid #ddd;
    padding: 1em 1.5em;
    margin: 1em 0 2em 0;
    border-radius: 4px;
}
#TOC > ul, nav#TOC > ul { padding-left: 1em; }
"""


class ExportError(Exception):
    """Raised when an export fails for any reason."""


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _check_pandoc() -> str:
    p = shutil.which("pandoc")
    if not p:
        raise ExportError(
            "pandoc is not installed on this host. "
            "Install with: apt-get install -y pandoc"
        )
    return p


def _extract_h1_title(source: Path) -> Optional[str]:
    """Return the text of the first '# ' line, or None."""
    try:
        with source.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r"^\s*#\s+(.+?)\s*#*\s*$", line)
                if m:
                    return m.group(1).strip()
    except OSError:
        return None
    return None


def _build_css(page_size: str, custom_style: Optional[Path]) -> Path:
    """Write CSS to a temp file and return its path. Caller owns cleanup."""
    if custom_style is not None:
        if not custom_style.is_file():
            raise ExportError(f"Custom style file not found: {custom_style}")
        return custom_style
    css = DEFAULT_CSS.replace("__PAGE_SIZE__", page_size.upper())
    fd, tmp = tempfile.mkstemp(suffix=".css", prefix="export-md-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(css)
    return Path(tmp)


def _pdf_engine() -> str:
    if shutil.which("wkhtmltopdf"):
        return "wkhtmltopdf"
    if shutil.which("weasyprint"):
        return "weasyprint"
    raise ExportError(
        "No PDF engine available. Install wkhtmltopdf "
        "(apt-get install wkhtmltopdf) or weasyprint (pip install weasyprint)."
    )


def _run_pandoc(cmd: Sequence[str], quiet: bool) -> None:
    if not quiet:
        print("→ " + " ".join(str(c) for c in cmd), file=sys.stderr)
    try:
        res = subprocess.run(
            list(cmd),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ExportError(f"pandoc invocation failed: {exc}") from exc
    if res.returncode != 0:
        msg = (res.stderr or res.stdout or "").strip()
        raise ExportError(f"pandoc failed (exit {res.returncode}): {msg}")


def _concat_pdfs(main_pdf: Path, extra_pdfs: Sequence[Path], quiet: bool) -> None:
    """Append extra_pdfs to main_pdf in place, each with a bookmark."""
    try:
        from pypdf import PdfWriter, PdfReader
    except ImportError as exc:
        raise ExportError(
            "pypdf is required for --embed-pdfs. Install with: pip install pypdf"
        ) from exc

    writer = PdfWriter()
    # Add main pdf first
    main_reader = PdfReader(str(main_pdf))
    writer.append(main_reader, outline_item=main_pdf.stem)
    for p in extra_pdfs:
        if not p.is_file():
            raise ExportError(f"Embed PDF not found: {p}")
        try:
            r = PdfReader(str(p))
        except Exception as exc:
            raise ExportError(f"Could not read embed PDF {p}: {exc}") from exc
        writer.append(r, outline_item=p.name)
        if not quiet:
            print(f"  embedded: {p.name} ({len(r.pages)} pages)", file=sys.stderr)

    tmp_out = main_pdf.with_suffix(".__merged.pdf")
    with tmp_out.open("wb") as f:
        writer.write(f)
    tmp_out.replace(main_pdf)


def _page_count(pdf_path: Path) -> Optional[int]:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def export(
    source: str | os.PathLike,
    to: str,
    output: Optional[str | os.PathLike] = None,
    *,
    title: Optional[str] = None,
    embed_pdfs: Optional[Iterable[str | os.PathLike]] = None,
    style: Optional[str | os.PathLike] = None,
    header: Optional[str] = None,
    footer: Optional[str] = None,
    page_size: str = "letter",
    no_toc: bool = False,
    quiet: bool = False,
) -> Path:
    """Convert a markdown file to PDF, DOCX, or HTML.

    Returns the absolute Path of the produced output file.
    Raises ExportError on any failure.
    """
    fmt = (to or "").lower().strip()
    if fmt not in VALID_FORMATS:
        raise ExportError(
            f"Invalid format {to!r}. Must be one of: {sorted(VALID_FORMATS)}"
        )

    page_size = (page_size or "letter").lower().strip()
    if page_size not in VALID_PAGE_SIZES:
        raise ExportError(
            f"Invalid page size {page_size!r}. Must be one of: {sorted(VALID_PAGE_SIZES)}"
        )

    src = Path(source).expanduser().resolve()
    if not src.is_file():
        raise ExportError(f"Source markdown not found: {src}")

    if embed_pdfs and fmt != "pdf":
        raise ExportError("--embed-pdfs is only valid when --to pdf")

    pandoc_bin = _check_pandoc()

    # Resolve output path
    if output is None:
        out = src.with_suffix("." + fmt)
    else:
        out = Path(output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    # Resolve title: explicit > H1 > filename stem
    effective_title = title or _extract_h1_title(src) or src.stem

    # Resolve CSS for html/pdf
    css_path: Optional[Path] = None
    cleanup_css = False
    if fmt in {"pdf", "html"}:
        custom = Path(style).expanduser().resolve() if style else None
        css_path = _build_css(page_size, custom)
        cleanup_css = style is None  # only cleanup our generated css

    try:
        cmd: list[str] = [
            pandoc_bin,
            str(src),
            "-o", str(out),
            "--metadata", f"title={effective_title}",
        ]
        if not no_toc:
            cmd.append("--toc")
        if header:
            cmd += ["--metadata", f"header={header}"]
        if footer:
            cmd += ["--metadata", f"footer={footer}"]

        if fmt == "pdf":
            engine = _pdf_engine()
            cmd += ["--pdf-engine=" + engine]
            if css_path is not None:
                cmd += ["--css", str(css_path)]
            # Embedded styling needs standalone mode (default for pdf via pandoc)
        elif fmt == "html":
            cmd += ["-s"]  # standalone (full HTML doc)
            if css_path is not None:
                cmd += ["--css", str(css_path),
                        "--embed-resources", "--standalone"]
        elif fmt == "docx":
            # docx ignores CSS; could support --reference-doc later
            pass

        _run_pandoc(cmd, quiet=quiet)

        if not out.is_file() or out.stat().st_size == 0:
            raise ExportError(f"Pandoc produced no output at {out}")

        # PDF concatenation step
        if fmt == "pdf" and embed_pdfs:
            extras = [Path(p).expanduser().resolve() for p in embed_pdfs]
            _concat_pdfs(out, extras, quiet=quiet)

    finally:
        if cleanup_css and css_path is not None:
            try:
                css_path.unlink()
            except OSError:
                pass

    if not quiet:
        size = out.stat().st_size
        msg = f"Exported {src} → {out} ({size:,} bytes"
        if fmt == "pdf":
            pages = _page_count(out)
            if pages is not None:
                msg += f", {pages} pages"
        msg += ")"
        print(msg)

    return out
