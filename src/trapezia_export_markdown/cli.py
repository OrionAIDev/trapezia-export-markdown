"""CLI: trapezia-export-markdown <source> --to {pdf,docx,html} [options]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._impl import export, ExportError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trapezia-export-markdown",
        description="Convert markdown to PDF, DOCX, or HTML.",
    )
    parser.add_argument("source", type=Path, help="Path to source markdown file")
    parser.add_argument(
        "--to", required=True, choices=["pdf", "docx", "html"],
        help="Output format",
    )
    parser.add_argument("--output", type=Path, default=None,
                        help="Output file path (default: <source>.<ext>)")
    parser.add_argument("--title", default=None,
                        help="Document title (default: extracted from first H1)")
    parser.add_argument("--embed-pdfs", type=Path, nargs="*", default=None,
                        help="PDFs to append after main content (PDF output only)")
    parser.add_argument("--style", type=Path, default=None,
                        help="Custom CSS file for HTML/PDF styling")
    parser.add_argument("--header", default=None, help="Page header text")
    parser.add_argument("--footer", default=None, help="Page footer text")
    parser.add_argument("--page-size", choices=["letter", "a4"], default="letter")
    parser.add_argument("--no-toc", action="store_true", help="Skip table of contents")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = export(
            source=args.source,
            to=args.to,
            output=args.output,
            embed_pdfs=args.embed_pdfs,
            title=args.title,
            style=args.style,
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
