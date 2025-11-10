"""Tests for file path utilities."""
from pathlib import Path
from src.utils.paths import get_data_dir, list_pdf_files


def test_get_data_dir():
    """Test data directory path retrieval."""
    data_dir = get_data_dir()
    assert isinstance(data_dir, Path)
    assert data_dir.name == "data"
    assert data_dir.exists()
    assert data_dir.is_dir()


def test_list_pdf_files():
    """Test PDF file listing."""
    # Should find our test PDF
    pdfs = list_pdf_files()
    assert len(pdfs) > 0
    assert all(pdf.suffix == ".pdf" for pdf in pdfs)
    
    # Test with subdirectory
    pdfs = list_pdf_files("test_subdir")
    assert isinstance(pdfs, list)  # Even if empty