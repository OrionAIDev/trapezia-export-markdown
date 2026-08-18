"""Tests for the trapezia-export-markdown CLI — run with: pytest tests/"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from trapezia_export_markdown.cli import main

HAVE_PANDOC = shutil.which("pandoc") is not None
requires_pandoc = pytest.mark.skipif(not HAVE_PANDOC, reason="pandoc not installed")


def _write_md(p: Path, body: str = "# Doc\n\nbody\n") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


@requires_pandoc
def test_cli_directory_basic(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    _write_md(src / "a.md")
    _write_md(src / "b.md")
    out_dir = tmp_path / "out"

    rc = main([str(src), "--to", "html", "--output", str(out_dir), "--quiet"])

    assert rc == 0
    assert (out_dir / "a.html").is_file()
    assert (out_dir / "b.html").is_file()


@requires_pandoc
def test_cli_directory_recursive(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    _write_md(src / "top.md")
    _write_md(src / "sub" / "deep.md")
    out_dir = tmp_path / "out"

    rc = main([str(src), "--to", "html", "--output", str(out_dir),
               "--recursive", "--quiet"])

    assert rc == 0
    assert (out_dir / "top.html").is_file()
    assert (out_dir / "deep.html").is_file()


@requires_pandoc
def test_cli_reference_doc_flag(tmp_path: Path) -> None:
    src = _write_md(tmp_path / "doc.md")
    ref = tmp_path / "template.docx"
    assert main([str(src), "--to", "docx", "--output", str(ref), "--quiet"]) == 0

    out = tmp_path / "styled.docx"
    rc = main([str(src), "--to", "docx", "--output", str(out),
               "--reference-doc", str(ref), "--quiet"])
    assert rc == 0
    assert out.read_bytes()[:4] == b"PK\x03\x04"


@requires_pandoc
def test_cli_template_alias(tmp_path: Path) -> None:
    src = _write_md(tmp_path / "doc.md")
    ref = tmp_path / "template.docx"
    assert main([str(src), "--to", "docx", "--output", str(ref), "--quiet"]) == 0

    out = tmp_path / "styled2.docx"
    rc = main([str(src), "--to", "docx", "--output", str(out),
               "--template", str(ref), "--quiet"])
    assert rc == 0
    assert out.is_file()
