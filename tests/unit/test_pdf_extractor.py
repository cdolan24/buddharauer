"""
Unit tests for the PDF text extraction module.
"""
import pytest
from pathlib import Path
from datetime import datetime
from src.pipeline.pdf_extractor import PDFExtractor, PDFMetadata, PDFPage


def test_pdf_metadata_creation():
    """Test PDFMetadata dataclass creation."""
    metadata = PDFMetadata(
        title="Test Document",
        author="Test Author",
        subject="Test Subject",
        keywords="test, pdf",
        creator="Test Creator",
        producer="Test Producer",
        creation_date=datetime.now(),
        modification_date=datetime.now(),
        page_count=10
    )
    
    assert metadata.title == "Test Document"
    assert metadata.author == "Test Author"
    assert metadata.page_count == 10


def test_pdf_page_creation():
    """Test PDFPage dataclass creation."""
    page = PDFPage(
        number=1,
        text="Test page content",
        is_scanned=False
    )
    
    assert page.number == 1
    assert page.text == "Test page content"
    assert page.is_scanned is False


def test_pdf_extraction():
    """Test PDF text extraction with a simple PDF file."""
    pdf_path = Path("tests/data/test.pdf")
    
    extractor = PDFExtractor()
    pages, metadata = extractor.extract_text(pdf_path)
    
    assert len(pages) > 0
    assert isinstance(metadata, PDFMetadata)
    assert pages[0].text.strip() == "Test PDF content"


def test_progress_callback():
    """Test progress callback functionality."""
    progress_calls = []
    
    def progress_callback(current, total):
        progress_calls.append((current, total))
    
    extractor = PDFExtractor(progress_callback=progress_callback)
    assert extractor.progress_callback is not None


def test_text_statistics():
    """Test text statistics calculation."""
    pages = [
        PDFPage(number=1, text="Page one content", is_scanned=False),
        PDFPage(number=2, text="", is_scanned=True),
        PDFPage(number=3, text="Page three", is_scanned=False),
    ]
    
    from src.pipeline.pdf_extractor import get_text_statistics
    stats = get_text_statistics(pages)
    
    assert stats["total_pages"] == 3
    assert stats["scanned_pages"] == 1
    assert stats["empty_pages"] == 1
    assert stats["total_chars"] == len("Page one content") + len("Page three")