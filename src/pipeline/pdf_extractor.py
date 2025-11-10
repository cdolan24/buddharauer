"""
PDF text extraction module for Buddharauer V2.
Handles extraction of text and metadata from PDF files using PyMuPDF.

All PDFs should be located within the data directory of the project.
Use src.utils.paths.get_data_dir() to get the correct path.
"""
from pathlib import Path
from typing import Dict, List, Optional
import fitz  # PyMuPDF
from dataclasses import dataclass
from datetime import datetime

from src.utils.paths import get_data_dir, list_pdf_files


@dataclass
class PDFMetadata:
    """Metadata extracted from a PDF document."""
    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    keywords: Optional[str]
    creator: Optional[str]
    producer: Optional[str]
    creation_date: Optional[datetime]
    modification_date: Optional[datetime]
    page_count: int


@dataclass
class PDFPage:
    """Represents a single page from a PDF document."""
    number: int
    text: str
    is_scanned: bool


class PDFExtractor:
    """Handles extraction of text and metadata from PDF files."""
    
    def __init__(self, progress_callback=None):
        """
        Initialize the PDF extractor.
        
        Args:
            progress_callback: Optional callback function(current, total) for progress tracking
        """
        self.progress_callback = progress_callback

    def extract_metadata(self, pdf_doc: fitz.Document) -> PDFMetadata:
        """
        Extract metadata from a PDF document.
        
        Args:
            pdf_doc: PyMuPDF document object
            
        Returns:
            PDFMetadata object containing document metadata
        """
        metadata = pdf_doc.metadata
        
        return PDFMetadata(
            title=metadata.get('title'),
            author=metadata.get('author'),
            subject=metadata.get('subject'),
            keywords=metadata.get('keywords'),
            creator=metadata.get('creator'),
            producer=metadata.get('producer'),
            creation_date=self._parse_pdf_date(metadata.get('creationDate')),
            modification_date=self._parse_pdf_date(metadata.get('modDate')),
            page_count=pdf_doc.page_count
        )

    def extract_text(self, pdf_path: Path) -> tuple[List[PDFPage], PDFMetadata]:
        """
        Extract text and metadata from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (list of PDFPage objects, PDFMetadata object)
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If file is not a valid PDF
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            pdf_doc = fitz.open(pdf_path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF file: {e}")

        metadata = self.extract_metadata(pdf_doc)
        pages = []

        for page_num in range(pdf_doc.page_count):
            if self.progress_callback:
                self.progress_callback(page_num + 1, pdf_doc.page_count)

            page = pdf_doc[page_num]
            text = page.get_text()
            
            # Heuristic for detecting scanned pages
            is_scanned = len(text.strip()) == 0 and bool(page.get_images())
            
            pages.append(PDFPage(
                number=page_num + 1,
                text=text,
                is_scanned=is_scanned
            ))

        pdf_doc.close()
        return pages, metadata

    def process_directory(self, 
                         subdir: Optional[str] = None, 
                         skip_existing: bool = True) -> Dict[Path, List[PDFPage]]:
        """
        Process all PDFs in the data directory or a subdirectory.
        
        Args:
            subdir: Optional subdirectory within data folder to process
            skip_existing: Skip PDFs that have already been processed
            
        Returns:
            Dictionary mapping PDF paths to their extracted pages
        """
        pdf_files = list_pdf_files(subdir)
        results = {}
        
        for pdf_path in pdf_files:
            try:
                pages, _ = self.extract_text(pdf_path)
                results[pdf_path] = pages
                if self.progress_callback:
                    self.progress_callback(len(results), len(pdf_files))
            except Exception as e:
                print(f"Error processing {pdf_path}: {e}")
                continue
                
        return results

    def _parse_pdf_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse PDF date string into datetime object.
        Handles common PDF date formats.
        
        Args:
            date_str: PDF date string or None
            
        Returns:
            datetime object or None if parsing fails
        """
        if not date_str:
            return None
            
        try:
            # Remove timezone info (D:YYYYMMDDHHmmSS+HH'mm')
            clean_date = date_str.replace("D:", "")[:14]
            return datetime.strptime(clean_date, "%Y%m%d%H%M%S")
        except (ValueError, AttributeError):
            return None


def get_text_statistics(pages: List[PDFPage]) -> Dict[str, int]:
    """
    Calculate basic statistics about the extracted text.
    
    Args:
        pages: List of PDFPage objects
        
    Returns:
        Dictionary with statistics (total_pages, total_chars, etc.)
    """
    total_chars = sum(len(page.text) for page in pages)
    scanned_pages = sum(1 for page in pages if page.is_scanned)
    empty_pages = sum(1 for page in pages if not page.text.strip())
    
    return {
        "total_pages": len(pages),
        "total_chars": total_chars,
        "scanned_pages": scanned_pages,
        "empty_pages": empty_pages,
        "avg_chars_per_page": total_chars // len(pages) if pages else 0
    }