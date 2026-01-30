"""
Unit Tests for PDF Client

Tests PDF text extraction, validation, and metadata retrieval.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pdfplumber

from clients.pdf_client import (
    extract_text_from_pdf,
    validate_pdf_file,
    get_pdf_metadata,
    is_scanned_pdf,
    clean_extracted_text,
)
from tests import TEST_DATA_DIR, SAMPLE_TRANSCRIPT_PATH


class TestPDFExtraction:
    """Test PDF text extraction functionality."""
    
    def test_extract_text_from_valid_pdf(self):
        """Test extracting text from a valid PDF."""
        # Skip if sample PDF doesn't exist
        if not SAMPLE_TRANSCRIPT_PATH.exists():
            pytest.skip("Sample transcript PDF not found")
        
        text = extract_text_from_pdf(SAMPLE_TRANSCRIPT_PATH)
        
        assert isinstance(text, str)
        assert len(text) > 0
        assert len(text.strip()) > 50  # Should have substantial content
    
    def test_extract_text_file_not_found(self):
        """Test error handling for non-existent file."""
        fake_path = TEST_DATA_DIR / "nonexistent.pdf"
        
        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf(fake_path)
    
    def test_extract_text_invalid_extension(self):
        """Test error handling for non-PDF file."""
        fake_path = TEST_DATA_DIR / "document.txt"
        
        # Create fake file
        fake_path.parent.mkdir(parents=True, exist_ok=True)
        fake_path.touch()
        
        with pytest.raises(ValueError, match="not a PDF"):
            extract_text_from_pdf(fake_path)
        
        # Cleanup
        fake_path.unlink()
    
    @patch('clients.pdf_client.pdfplumber.open')
    def test_extract_text_empty_pdf(self, mock_pdfplumber):
        """Test handling of empty PDF with no pages."""
        # Mock empty PDF
        mock_pdf = MagicMock()
        mock_pdf.pages = []
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        result = extract_text_from_pdf(SAMPLE_TRANSCRIPT_PATH)
        
        assert result == ""
    
    @patch('clients.pdf_client.pdfplumber.open')
    def test_extract_text_multi_page(self, mock_pdfplumber):
        """Test extraction from multi-page PDF."""
        # Mock multi-page PDF
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        result = extract_text_from_pdf(SAMPLE_TRANSCRIPT_PATH)
        
        assert "Page 1 content" in result
        assert "Page 2 content" in result
        assert "--- Page 2 ---" in result  # Page separator


class TestPDFValidation:
    """Test PDF validation functionality."""
    
    def test_validate_valid_pdf(self):
        """Test validation of a valid PDF file."""
        if not SAMPLE_TRANSCRIPT_PATH.exists():
            pytest.skip("Sample transcript PDF not found")
        
        is_valid, error = validate_pdf_file(SAMPLE_TRANSCRIPT_PATH)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_nonexistent_file(self):
        """Test validation of non-existent file."""
        fake_path = TEST_DATA_DIR / "nonexistent.pdf"
        
        is_valid, error = validate_pdf_file(fake_path)
        
        assert is_valid is False
        assert "not found" in error.lower()
    
    def test_validate_wrong_extension(self):
        """Test validation rejects non-PDF files."""
        fake_path = TEST_DATA_DIR / "document.txt"
        fake_path.parent.mkdir(parents=True, exist_ok=True)
        fake_path.touch()
        
        is_valid, error = validate_pdf_file(fake_path)
        
        assert is_valid is False
        assert "not a PDF" in error
        
        # Cleanup
        fake_path.unlink()
    
    @patch('clients.pdf_client.pdfplumber.open')
    def test_validate_empty_pdf(self, mock_pdfplumber):
        """Test validation of PDF with no pages."""
        mock_pdf = MagicMock()
        mock_pdf.pages = []
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        is_valid, error = validate_pdf_file(SAMPLE_TRANSCRIPT_PATH)
        
        assert is_valid is False
        assert "no pages" in error.lower()


class TestPDFMetadata:
    """Test PDF metadata extraction."""
    
    @patch('clients.pdf_client.pdfplumber.open')
    def test_get_metadata_success(self, mock_pdfplumber):
        """Test successful metadata extraction."""
        # Mock PDF with metadata
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(), MagicMock()]  # 2 pages
        mock_pdf.metadata = {
            "Title": "Student Transcript",
            "Author": "School System",
            "Creator": "PDF Generator",
        }
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf
        
        # Mock extract_text_from_pdf
        with patch('clients.pdf_client.extract_text_from_pdf', return_value="Sample text content"):
            metadata = get_pdf_metadata(SAMPLE_TRANSCRIPT_PATH)
        
        assert metadata["num_pages"] == 2
        assert metadata["title"] == "Student Transcript"
        assert metadata["author"] == "School System"
        assert metadata["readable"] is True
    
    def test_get_metadata_file_size(self):
        """Test file size calculation in metadata."""
        if not SAMPLE_TRANSCRIPT_PATH.exists():
            pytest.skip("Sample transcript PDF not found")
        
        metadata = get_pdf_metadata(SAMPLE_TRANSCRIPT_PATH)
        
        assert "file_size_bytes" in metadata
        assert metadata["file_size_bytes"] > 0
        assert metadata["file_size_mb"] >= 0  # Could be 0 for very small files


class TestHelperFunctions:
    """Test helper utility functions."""
    
    @patch('clients.pdf_client.extract_text_from_pdf')
    def test_is_scanned_pdf_true(self, mock_extract):
        """Test detection of scanned PDF (no text)."""
        mock_extract.return_value = "   "  # Only whitespace
        
        result = is_scanned_pdf(SAMPLE_TRANSCRIPT_PATH)
        
        assert result is True
    
    @patch('clients.pdf_client.extract_text_from_pdf')
    def test_is_scanned_pdf_false(self, mock_extract):
        """Test detection of text-based PDF."""
        # Text must be > 100 characters (default threshold)
        mock_extract.return_value = "This is substantial text content that clearly exceeds the 100 character threshold needed to determine that this is not a scanned PDF document."
        
        result = is_scanned_pdf(SAMPLE_TRANSCRIPT_PATH)
        
        assert result is False
    
    def test_clean_extracted_text(self):
        """Test text cleaning function."""
        dirty_text = """
        Line 1
        
        
        
        Line 2
        
        Multiple    spaces    here
        1
        Page number alone
        """
        
        cleaned = clean_extracted_text(dirty_text)
        
        # Should remove excessive newlines
        assert "\n\n\n" not in cleaned
        
        # Should reduce multiple spaces
        assert "    " not in cleaned
        
        # Should be trimmed
        assert cleaned == cleaned.strip()
    
    def test_clean_extracted_text_empty(self):
        """Test cleaning empty text."""
        result = clean_extracted_text("")
        assert result == ""
        
        result = clean_extracted_text(None)
        assert result == ""


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestPDFClientIntegration:
    """Integration tests using real PDF file."""
    
    @pytest.fixture
    def sample_pdf_path(self):
        """Fixture providing path to sample PDF."""
        if not SAMPLE_TRANSCRIPT_PATH.exists():
            pytest.skip("Sample transcript PDF not found")
        return SAMPLE_TRANSCRIPT_PATH
    
    def test_full_pdf_workflow(self, sample_pdf_path):
        """Test complete workflow: validate → extract → get metadata."""
        # Step 1: Validate
        is_valid, error = validate_pdf_file(sample_pdf_path)
        assert is_valid, f"PDF validation failed: {error}"
        
        # Step 2: Extract text
        text = extract_text_from_pdf(sample_pdf_path)
        assert len(text) > 0, "No text extracted"
        
        # Step 3: Get metadata
        metadata = get_pdf_metadata(sample_pdf_path)
        assert metadata["num_pages"] > 0
        assert metadata["has_text"] is True
        
        # Verify consistency
        assert len(text) == metadata["char_count"]
