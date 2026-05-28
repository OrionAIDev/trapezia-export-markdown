# trapezia-export-markdown

Convert markdown files to **PDF**, **DOCX**, or **HTML** with a clean,
clinician-friendly default style. Supports appending raw PDFs after the main
content — designed for medical-record packet bundling but generally useful.

This is the packaged form of the OrionLab `export-markdown` skill, decoupled
from `sys.path` tricks so it can be `pip install`ed and imported normally.

## Installation

```bash
pip install "git+https://github.com/OrionAIDev/trapezia-export-markdown@v1.0.0"
```

Or pin via `requirements.txt`:

```
trapezia-export-markdown @ git+https://github.com/OrionAIDev/trapezia-export-markdown@v1.0.0
```

### System requirements (NOT pip-installable)

You must install these on the host yourself:

| Tool | Purpose | Install |
|------|---------|---------|
| **pandoc** | Required for all formats | `apt-get install -y pandoc` |
| **wkhtmltopdf** | PDF engine (preferred) | `apt-get install -y wkhtmltopdf` |
| **weasyprint** | PDF engine (fallback) | `apt-get install -y weasyprint` |

DOCX and HTML need only `pandoc`. PDF needs `pandoc` plus one PDF engine.

## Public API

```python
from pathlib import Path
from trapezia_export_markdown import export, ExportError

# Markdown to PDF
out = export(Path("report.md"), to="pdf", output=Path("report.pdf"))
print(out)  # /abs/path/to/report.pdf

# Markdown to DOCX
export(Path("memo.md"), to="docx", output=Path("memo.docx"))

# Markdown to HTML (standalone, self-contained)
export(Path("page.md"), to="html", output=Path("page.html"))

# PDF with custom title + page size + footer
export(
    Path("packet.md"),
    to="pdf",
    output=Path("packet.pdf"),
    title="Patient Packet — Dr. Varano 2026-06-10",
    page_size="letter",
    footer="Confidential — Chris Advena",
)
```

### Embedding raw PDFs (packet-generator pattern)

For the medical-diary packet generator and similar workflows, you can append
raw record PDFs after the main markdown content. Each embedded PDF gets a
bookmark named after its filename.

```python
from pathlib import Path
from trapezia_export_markdown import export

export(
    Path("packet-cover.md"),
    to="pdf",
    output=Path("appointment-2026-06-10.pdf"),
    title="Dr. Varano Appointment Packet — 2026-06-10",
    embed_pdfs=[
        Path("raw-record-jefferson-2026-05-12.pdf"),
        Path("raw-record-mainline-2026-04-30.pdf"),
    ],
)
```

Only valid when `to="pdf"`. Other formats raise `ExportError`.

## Catching failures

All recoverable failures raise `ExportError`:

```python
from trapezia_export_markdown import export, ExportError

try:
    export(Path("missing.md"), to="pdf", output=Path("out.pdf"))
except ExportError as e:
    # e.g. "Source markdown not found: ..."
    # e.g. "pandoc is not installed on this host. ..."
    # e.g. "No PDF engine available. ..."
    log.warning("Export skipped: %s", e)
```

## CLI

After install, the `trapezia-export-markdown` command is on `$PATH`:

```bash
trapezia-export-markdown report.md --to pdf --output report.pdf
trapezia-export-markdown report.md --to docx
trapezia-export-markdown report.md --to html --no-toc --quiet
trapezia-export-markdown cover.md --to pdf --output packet.pdf \
    --embed-pdfs raw1.pdf raw2.pdf \
    --title "My Packet" --footer "Confidential"
```

Options:

| Flag | Meaning |
|------|---------|
| `--to {pdf,docx,html}` | Output format (required) |
| `--output PATH` | Output path (default: source with extension swapped) |
| `--title TEXT` | Document title (default: extracted from first H1) |
| `--embed-pdfs PATH...` | PDFs to append after main content (PDF only) |
| `--style PATH` | Custom CSS file (HTML/PDF) |
| `--header TEXT` | Page header text |
| `--footer TEXT` | Page footer text |
| `--page-size {letter,a4}` | Page size (default: letter) |
| `--no-toc` | Skip table of contents |
| `--quiet` | Suppress progress output |

## Default styling

Out of the box, the produced PDF/HTML uses a clinical default style — serif
body (Georgia), sans headings (Helvetica), 1-inch margins, automatic table of
contents, page-number footer. Override entirely with `--style your.css`.

## Tests

```bash
pip install "trapezia-export-markdown[test]"
pytest tests/
```

Tests that require pandoc/wkhtmltopdf/pypdf are auto-skipped if the
dependency is missing.

## License

MIT — see [LICENSE](LICENSE).
