"""trapezia_export_markdown — markdown to PDF/DOCX/HTML.

Public API:
    from trapezia_export_markdown import export, ExportError
"""
from ._impl import export, ExportError

__all__ = ["export", "ExportError"]
__version__ = "1.0.0"
