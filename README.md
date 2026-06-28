# trapezia-export-markdown

Convert markdown — a single file or a whole folder — to **PDF**, **DOCX**, or
**HTML** with a clean, clinician-friendly default style. Supports appending raw
PDFs after the main content (medical-record packet bundling), DOCX
reference-template styling, and batch directory conversion.

This is the packaged form of the OrionLab `export-markdown` skill, decoupled
from `sys.path` tricks so it can be `pip install`ed and imported normally.

## Installation

```bash
pip install "git+https://github.com/OrionAIDev/trapezia-export-markdown@v1.1.0"
```

Or pin via `requirements.txt`:

```
trapezia-export-markdown @ git+https://github.com/OrionAIDev/trapezia-export-markdown@v1.1.0
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

### DOCX reference template (styling)

For branded/styled Word output, pass a `.docx` whose styles pandoc should reuse
(pandoc `--reference-doc`). Valid only when `to="docx"`.

```python
from pathlib import Path
from trapezia_export_markdown import export

export(
    Path("memo.md"),
    to="docx",
    output=Path("memo.docx"),
    reference_doc=Path("house-style.docx"),
)
```

### Batch / whole-folder conversion

`export_dir` converts every markdown file in a directory. Outputs default to a
`export/` subfolder; pass `output_dir` to redirect. Extra keyword arguments are
forwarded to `export` for each file.

```python
from pathlib import Path
from trapezia_export_markdown import export_dir

# Convert every .md in ./docs to PDF, writing to ./docs/export/
paths = export_dir(Path("docs"), to="pdf")

# Recurse, into a custom output dir, with a DOCX template
paths = export_dir(
    Path("docs"),
    to="docx",
    output_dir=Path("rendered"),
    recursive=True,
    reference_doc=Path("house-style.docx"),
)
```

Raises `ExportError` if the directory is missing or contains no matching files,
or if any single file fails to convert.

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

# DOCX with a reference template
trapezia-export-markdown memo.md --to docx --reference-doc house-style.docx

# Whole folder (source is a directory) — outputs to ./docs/export/
trapezia-export-markdown docs/ --to pdf
trapezia-export-markdown docs/ --to docx --recursive --output rendered/ \
    --template house-style.docx
```

Options:

| Flag | Meaning |
|------|---------|
| `--to {pdf,docx,html}` | Output format (required) |
| `--output PATH` | Output path, or output **directory** when source is a folder |
| `--title TEXT` | Document title (default: extracted from first H1) |
| `--embed-pdfs PATH...` | PDFs to append after main content (PDF only) |
| `--style PATH` | Custom CSS file (HTML/PDF) |
| `--reference-doc PATH` / `--template PATH` | Reference `.docx` for styling (DOCX only) |
| `--header TEXT` | Page header text |
| `--footer TEXT` | Page footer text |
| `--page-size {letter,a4}` | Page size (default: letter) |
| `--recursive` | Recurse into subdirectories (folder source only) |
| `--pattern GLOB` | Markdown glob (folder source only; default `*.md`) |
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
