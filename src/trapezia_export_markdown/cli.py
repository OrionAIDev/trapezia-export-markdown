"""CLI: trapezia-export-markdown <source> --to {pdf,docx,html} [options]

``source`` may be a single markdown file or a directory. When it is a
directory, every matching markdown file is converted (see ``--recursive`` /
``--pattern``) and ``--output`` is treated as the output directory.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._impl import export, export_dir, ExportError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trapezia-export-markdown",
        description="Convert markdown (a file or a whole folder) to PDF, DOCX, or HTML.",
    )
    parser.add_argument("source", type=Path,
                        help="Source markdown file, or a directory of them")
    parser.add_argument(
        "--to", required=True, choices=["pdf", "docx", "html"],
        help="Output format",
    )
    parser.add_argument("--output", type=Path, default=None,
                        help="Output file path, or output directory when source "
                             "is a folder (default: <source>.<ext>, or "
                             "<source_dir>/export/)")
    parser.add_argument("--title", default=None,
                        help="Document title (default: extracted from first H1)")
    parser.add_argument("--embed-pdfs", type=Path, nargs="*", default=None,
                        help="PDFs to append after main content (PDF output only)")
    parser.add_argument("--style", type=Path, default=None,
                        help="Custom CSS file for HTML/PDF styling")
    parser.add_argument("--reference-doc", "--template", dest="reference_doc",
                        type=Path, default=None,
                        help="Reference .docx supplying styles for DOCX output "
                             "(DOCX only)")
    parser.add_argument("--header", default=None, help="Page header text")
    parser.add_argument("--footer", default=None, help="Page footer text")
    parser.add_argument("--page-size", choices=["letter", "a4"], default="letter")
    parser.add_argument("--no-toc", action="store_true", help="Skip table of contents")
    parser.add_argument("--recursive", action="store_true",
                        help="Recurse into subdirectories (folder source only)")
    parser.add_argument("--pattern", default="*.md",
                        help="Glob for markdown files (folder source only; default *.md)")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.source.is_dir():
            results = export_dir(
                source_dir=args.source,
                to=args.to,
                output_dir=args.output,
                recursive=args.recursive,
                pattern=args.pattern,
                title=args.title,
                style=args.style,
                reference_doc=args.reference_doc,
                header=args.header,
                footer=args.footer,
                page_size=args.page_size,
                no_toc=args.no_toc,
                quiet=args.quiet,
            )
            if not args.quiet:
                print(f"Exported {len(results)} file(s) from {args.source}")
            return 0

        result = export(
            source=args.source,
            to=args.to,
            output=args.output,
            embed_pdfs=args.embed_pdfs,
            title=args.title,
            style=args.style,
            reference_doc=args.reference_doc,
            header=args.header,
            footer=args.footer,
            page_size=args.page_size,
            no_toc=args.no_toc,
            quiet=args.quiet,
        )
        if not args.quiet:
            print(f"Exported {args.source} -> {result}")
        return 0
    except ExportError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
