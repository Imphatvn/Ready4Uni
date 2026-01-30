"""
Utility Clients Module

This module contains low-level utility clients for external services
and file processing. These are pure utility functions that don't contain
business logic.

Clients:
- PDF Client: Extract text from PDF files using pdfplumber
"""

from .pdf_client import (
    extract_text_from_pdf,
    validate_pdf_file,
    get_pdf_metadata,
)

__all__ = [
    "extract_text_from_pdf",
    "validate_pdf_file",
    "get_pdf_metadata",
]
