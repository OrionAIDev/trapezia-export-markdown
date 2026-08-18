"""trapezia_export_markdown — markdown to PDF/DOCX/HTML.

Public API:
    from trapezia_export_markdown import export, export_dir, ExportError
"""
from ._impl import ExportError, export, export_dir

__all__ = ["export", "export_dir", "ExportError"]
__version__ = "1.1.1"
