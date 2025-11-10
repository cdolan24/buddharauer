"""
Unit tests for PDF extraction error handling and retry logic.
"""
import pytest
from pathlib import Path
import fitz
from unittest.mock import Mock, patch
from datetime import datetime

from src.pipeline.pdf_extractor import PDFExtractor
from src.pipeline.pdf_errors import (
    PDFExtractionError, PDFCorruptedError, PDFEncryptedError,
    PDFInvalidFormatError, PDFExtractionTimeout
)

# Mock PDF files for testing
VALID_PDF = Path("tests/data/test.pdf")
CORRUPTED_PDF = Path("tests/data/corrupted.pdf")
ENCRYPTED_PDF = Path("tests/data/encrypted.pdf")
INVALID_PDF = Path("tests/data/not_a_pdf.txt")

def test_corrupted_pdf():
    """Test handling of corrupted PDF files."""
    extractor = PDFExtractor()
    
    with pytest.raises(PDFCorruptedError) as exc:
        with patch('fitz.open', side_effect=fitz.FileDataError("corrupted file")):
            extractor.extract_text(VALID_PDF)
    
    assert "PDF file is corrupted" in str(exc.value)

def test_encrypted_pdf():
    """Test handling of encrypted PDF files."""
    extractor = PDFExtractor()
    
    mock_doc = Mock()
    mock_doc.needs_pass = True
    
    with pytest.raises(PDFEncryptedError) as exc:
        with patch('fitz.open', return_value=mock_doc):
            extractor.extract_text(VALID_PDF)
    
    assert "PDF is encrypted" in str(exc.value)

def test_invalid_pdf():
    """Test handling of non-PDF files."""
    extractor = PDFExtractor()
    
    mock_doc = Mock()
    mock_doc.needs_pass = False
    mock_doc.is_pdf = False
    
    with pytest.raises(PDFInvalidFormatError) as exc:
        with patch('fitz.open', return_value=mock_doc):
            extractor.extract_text(VALID_PDF)
    
    assert "Not a valid PDF" in str(exc.value)

def test_extraction_timeout():
    """Test handling of extraction timeouts."""
    extractor = PDFExtractor(timeout=0.1)  # Very short timeout
    
    with pytest.raises(PDFExtractionTimeout) as exc:
        with patch('time.time', side_effect=[0, 1]):  # Simulate 1 second elapsed
            extractor.extract_text(VALID_PDF)
    
    assert "PDF extraction timed out" in str(exc.value)

def test_retry_logic():
    """Test retry behavior on temporary failures."""
    extractor = PDFExtractor(max_retries=3)
    mock_fail = Mock(side_effect=[
        PDFExtractionError("temp error"),
        PDFExtractionError("temp error"),
        "success"
    ])
    
    with patch.object(PDFExtractor, 'extract_text', side_effect=mock_fail):
        result = extractor.extract_text(VALID_PDF)
    
    assert result == "success"
    assert mock_fail.call_count == 3

def test_progress_tracking():
    """Test progress callback functionality."""
    progress_calls = []
    def progress_callback(current, total):
        progress_calls.append((current, total))
    
    extractor = PDFExtractor(progress_callback=progress_callback)
    
    # Mock multiple PDF files
    pdf_files = [Path(f"test{i}.pdf") for i in range(3)]
    
    with patch('src.pipeline.pdf_extractor.list_pdf_files', return_value=pdf_files):
        with patch.object(PDFExtractor, 'extract_text', return_value=([], None)):
            extractor.process_directory()
    
    # Check progress tracking
    assert len(progress_calls) == 3
    assert progress_calls == [(1, 3), (2, 3), (3, 3)]

def test_directory_processing_with_errors():
    """Test directory processing with mixed success/failure."""
    extractor = PDFExtractor()
    
    # Mock PDF files with mixed results
    pdf_files = [Path(f"test{i}.pdf") for i in range(3)]
    
    def mock_extract(path):
        if "test0" in str(path):
            raise PDFCorruptedError("corrupted")
        elif "test1" in str(path):
            raise PDFEncryptedError("encrypted")
        else:
            return ([], None)
    
    with patch('src.pipeline.pdf_extractor.list_pdf_files', return_value=pdf_files):
        with patch.object(PDFExtractor, 'extract_text', side_effect=mock_extract):
            results = extractor.process_directory()
    
    # Only one file should have succeeded
    assert len(results) == 1
    assert Path("test2.pdf") in [p.name for p in results.keys()]