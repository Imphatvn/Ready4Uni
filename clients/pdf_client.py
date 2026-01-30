"""
PDF Client - PDF Text Extraction Utility

Handles PDF file processing using pdfplumber.
Provides text extraction, validation, and metadata retrieval.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
import pdfplumber

logger = logging.getLogger(__name__)


# ============================================================================
# PDF TEXT EXTRACTION
# ============================================================================

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract all text content from a PDF file.
    
    Uses pdfplumber to extract text from all pages and concatenates
    them with page separators.
    
    Args:
        file_path: Path to the PDF file (string or Path object)
        
    Returns:
        Extracted text as a single string
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        ValueError: If the file is not a valid PDF
        Exception: For other PDF processing errors
        
    Example:
        >>> text = extract_text_from_pdf("/tmp/transcript.pdf")
        >>> print(text[:100])
        "Student Name: João Silva
         School: Escola Secundária...
    """
    file_path = Path(file_path)
    
    # Validate file exists
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    # Validate file extension
    if file_path.suffix.lower() != '.pdf':
        raise ValueError(f"File is not a PDF: {file_path.suffix}")
    
    logger.info(f"📄 Extracting text from PDF: {file_path.name}")
    
    try:
        all_text = []
        
        with pdfplumber.open(file_path) as pdf:
            # Check if PDF has pages
            if len(pdf.pages) == 0:
                logger.warning("⚠️  PDF has no pages")
                return ""
            
            logger.debug(f"PDF has {len(pdf.pages)} page(s)")
            
            # Extract text from each page
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    page_text = page.extract_text()
                    
                    if page_text:
                        # Add page separator for multi-page documents
                        if page_num > 1:
                            all_text.append(f"\n--- Page {page_num} ---\n")
                        all_text.append(page_text)
                    else:
                        logger.debug(f"Page {page_num} has no extractable text")
                
                except Exception as e:
                    logger.warning(f"⚠️  Failed to extract text from page {page_num}: {e}")
                    continue
        
        # Combine all text
        full_text = "\n".join(all_text)
        
        if not full_text.strip():
            logger.warning("⚠️  No text extracted from PDF (might be scanned images)")
            return ""
        
        logger.info(f"✅ Extracted {len(full_text)} characters from PDF")
        return full_text
    
    except Exception as e:
        logger.error(f"❌ PDF extraction failed: {e}", exc_info=True)
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


# ============================================================================
# PDF VALIDATION
# ============================================================================

def validate_pdf_file(file_path: str) -> tuple[bool, Optional[str]]:
    """
    Validate a PDF file for readability and content.
    
    Checks:
    - File exists and is readable
    - File is a valid PDF
    - PDF has at least one page
    - PDF contains extractable text
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
        
    Example:
        >>> is_valid, error = validate_pdf_file("/tmp/transcript.pdf")
        >>> if not is_valid:
        ...     print(f"Invalid PDF: {error}")
    """
    file_path = Path(file_path)
    
    # Check file exists
    if not file_path.exists():
        return False, f"File not found: {file_path}"
    
    # Check file extension
    if file_path.suffix.lower() != '.pdf':
        return False, f"File is not a PDF (extension: {file_path.suffix})"
    
    # Check file size (not too small, not too large)
    file_size = file_path.stat().st_size
    if file_size < 100:  # Less than 100 bytes
        return False, "PDF file is too small (might be corrupted)"
    
    if file_size > 50 * 1024 * 1024:  # More than 50MB
        return False, "PDF file is too large (max 50MB)"
    
    try:
        # Try to open and read the PDF
        with pdfplumber.open(file_path) as pdf:
            # Check has pages
            if len(pdf.pages) == 0:
                return False, "PDF has no pages"
            
            # Check if at least first page has text
            first_page_text = pdf.pages[0].extract_text()
            if not first_page_text or len(first_page_text.strip()) < 10:
                return False, "PDF appears to be empty or contains only images (OCR required)"
        
        return True, None
    
    except Exception as e:
        return False, f"Failed to read PDF: {str(e)}"


# ============================================================================
# PDF METADATA
# ============================================================================

def get_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata from a PDF file.
    
    Retrieves information like:
    - Number of pages
    - File size
    - Creation date (if available)
    - Author (if available)
    - Character count
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Dictionary with metadata
        
    Example:
        >>> metadata = get_pdf_metadata("/tmp/transcript.pdf")
        >>> print(f"Pages: {metadata['num_pages']}")
        >>> print(f"Characters: {metadata['char_count']}")
    """
    file_path = Path(file_path)
    
    metadata = {
        "filename": file_path.name,
        "file_size_bytes": 0,
        "file_size_mb": 0.0,
        "num_pages": 0,
        "char_count": 0,
        "has_text": False,
        "readable": False,
    }
    
    try:
        # File size
        metadata["file_size_bytes"] = file_path.stat().st_size
        metadata["file_size_mb"] = round(metadata["file_size_bytes"] / (1024 * 1024), 2)
        
        # PDF-specific metadata
        with pdfplumber.open(file_path) as pdf:
            metadata["num_pages"] = len(pdf.pages)
            metadata["readable"] = True
            
            # PDF info (if available)
            if pdf.metadata:
                metadata["title"] = pdf.metadata.get("Title", "")
                metadata["author"] = pdf.metadata.get("Author", "")
                metadata["creator"] = pdf.metadata.get("Creator", "")
                metadata["creation_date"] = pdf.metadata.get("CreationDate", "")
            
            # Extract text to count characters
            try:
                text = extract_text_from_pdf(file_path)
                metadata["char_count"] = len(text)
                metadata["has_text"] = len(text.strip()) > 0
            except:
                pass
        
        logger.debug(f"PDF metadata: {metadata['num_pages']} pages, {metadata['char_count']} chars")
        
    except Exception as e:
        logger.warning(f"⚠️  Could not extract full metadata: {e}")
        metadata["error"] = str(e)
    
    return metadata


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_scanned_pdf(file_path: str, threshold: int = 100) -> bool:
    """
    Check if a PDF is likely a scanned image (no extractable text).
    
    Args:
        file_path: Path to the PDF file
        threshold: Minimum character count to consider as text-based
        
    Returns:
        True if likely scanned, False if has extractable text
    """
    try:
        text = extract_text_from_pdf(file_path)
        return len(text.strip()) < threshold
    except:
        return True  # If can't extract, assume scanned


def clean_extracted_text(text: str) -> str:
    """
    Clean up extracted PDF text by removing extra whitespace and artifacts.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove multiple consecutive newlines
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove excessive spaces
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove page numbers that appear alone on lines
    text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text
