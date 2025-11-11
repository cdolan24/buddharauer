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

    # Create a mock document that needs a password
    mock_doc = Mock()
    mock_doc.needs_pass = True
    mock_doc.is_pdf = True
    mock_doc.page_count = 1
    mock_doc.__enter__ = Mock(return_value=mock_doc)
    mock_doc.__exit__ = Mock(return_value=None)

    # Due to retry decorator, PDFEncryptedError gets wrapped in PDFExtractionError
    with pytest.raises(PDFExtractionError) as exc:
        with patch('fitz.open', return_value=mock_doc):
            extractor.extract_text(VALID_PDF)

    assert "PDF is encrypted" in str(exc.value)

def test_invalid_pdf():
    """Test handling of non-PDF files."""
    extractor = PDFExtractor()

    # Create a mock document that is not a PDF
    mock_doc = Mock()
    mock_doc.needs_pass = False
    mock_doc.is_pdf = False
    mock_doc.page_count = 0
    mock_doc.__enter__ = Mock(return_value=mock_doc)
    mock_doc.__exit__ = Mock(return_value=None)

    # Due to retry decorator, PDFInvalidFormatError gets wrapped in PDFExtractionError
    with pytest.raises(PDFExtractionError) as exc:
        with patch('fitz.open', return_value=mock_doc):
            extractor.extract_text(VALID_PDF)

    assert "Not a valid PDF" in str(exc.value)

def test_extraction_timeout():
    """Test handling of extraction timeouts."""
    extractor = PDFExtractor(timeout=0.1)  # Very short timeout

    # Create a mock document
    mock_doc = Mock()
    mock_doc.needs_pass = False
    mock_doc.is_pdf = True
    mock_doc.page_count = 1
    mock_doc.metadata = {}
    mock_doc.__enter__ = Mock(return_value=mock_doc)
    mock_doc.__exit__ = Mock(return_value=None)

    # Mock time.time to simulate timeout
    # Note: needs enough calls for the retry loop (3 attempts) x 2 calls per attempt
    time_values = [0, 0.2] * 6  # Exceed timeout on each attempt

    with pytest.raises(PDFExtractionError) as exc:  # Wrapped by retry decorator
        with patch('fitz.open', return_value=mock_doc):
            with patch('time.time', side_effect=time_values):
                extractor.extract_text(VALID_PDF)

    assert "timed out" in str(exc.value).lower()

def test_retry_logic():
    """Test retry behavior on temporary failures."""
    from src.pipeline.recovery import with_retry_sync

    # Create a mock function that fails twice then succeeds
    call_count = [0]
    @with_retry_sync(max_retries=2, initial_delay=0.01)
    def mock_operation():
        call_count[0] += 1
        if call_count[0] < 3:
            raise PDFExtractionError("temp error")
        return "success"

    result = mock_operation()

    assert result == "success"
    # with_retry_sync counts max_retries differently - it's max_retries + 1 total attempts
    # First attempt + 2 retries = 3 attempts total
    assert call_count[0] == 3

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
        """Mock extract_text to return proper structure for successful extraction."""
        if "test0" in str(path):
            raise PDFCorruptedError("corrupted")
        elif "test1" in str(path):
            raise PDFEncryptedError("encrypted")
        else:
            # Return a proper PDFMetadata object with all required fields
            from src.pipeline.pdf_extractor import PDFMetadata
            from datetime import datetime
            metadata = PDFMetadata(
                title="Test",
                author="Test Author",
                subject="Test Subject",
                keywords="test, pdf",
                creator="Test Creator",
                producer="Test Producer",
                creation_date=datetime.now(),
                modification_date=datetime.now(),
                page_count=1
            )
            return ([], metadata)

    with patch('src.pipeline.pdf_extractor.list_pdf_files', return_value=pdf_files):
        with patch.object(PDFExtractor, 'extract_text', side_effect=mock_extract):
            results = extractor.process_directory()

    # Only one file should have succeeded
    assert len(results) == 1
    # Compare string representations, not Path objects
    result_filenames = [p.name for p in results.keys()]
    assert "test2.pdf" in result_filenames