"""
PDF text extraction module for Buddharauer V2.
Handles extraction of text and metadata from PDF files using PyMuPDF.

All PDFs should be located within the data directory of the project.
Use src.utils.paths.get_data_dir() to get the correct path.
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
import fitz  # PyMuPDF
from dataclasses import dataclass
from datetime import datetime
import time

from src.utils.paths import get_data_dir, list_pdf_files
from src.utils.logging import get_logger
from .pdf_errors import (
    PDFExtractionError, PDFCorruptedError, PDFEncryptedError,
    PDFInvalidFormatError, PDFExtractionTimeout
)
from .recovery import with_retry_sync

logger = get_logger(__name__)


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
    
    def __init__(self, 
                progress_callback: Optional[Callable[[int, int], None]] = None,
                max_retries: int = 3,
                timeout: float = 30.0):
        """
        Initialize the PDF extractor.
        
        Args:
            progress_callback: Optional callback function(current, total) for progress tracking
            max_retries: Maximum number of retries for failed extractions
            timeout: Timeout in seconds for PDF operations
        """
        self.progress_callback = progress_callback
        self.max_retries = max_retries
        self.timeout = timeout

    def extract_metadata(self, pdf_doc: fitz.Document | Path) -> PDFMetadata:
        """
        Extract metadata from a PDF document.

        Args:
            pdf_doc: PyMuPDF document object or Path to PDF file

        Returns:
            PDFMetadata object containing document metadata

        Raises:
            PDFCorruptedError: If PDF file is corrupted
            PDFEncryptedError: If PDF file is encrypted
            PDFInvalidFormatError: If file is not a valid PDF
        """
        # Handle both Path and Document objects for flexibility
        should_close = False
        if isinstance(pdf_doc, Path):
            if not pdf_doc.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_doc}")
            try:
                pdf_doc = fitz.open(pdf_doc)
                should_close = True

                # Check if PDF is encrypted
                if pdf_doc.needs_pass:
                    raise PDFEncryptedError(f"PDF is encrypted: {pdf_doc}")

                # Check if PDF is valid
                if not pdf_doc.is_pdf:
                    raise PDFInvalidFormatError(f"Not a valid PDF: {pdf_doc}")
            except fitz.FileDataError as e:
                raise PDFCorruptedError(f"PDF file is corrupted: {e}")

        metadata = pdf_doc.metadata

        result = PDFMetadata(
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

        if should_close:
            pdf_doc.close()

        return result

    def extract_pages(self, pdf_path: Path) -> List[PDFPage]:
        """
        Extract pages from a PDF file (convenience method that calls extract_text).

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of PDFPage objects

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            PDFCorruptedError: If the PDF file is corrupted
            PDFEncryptedError: If the PDF file is encrypted
            PDFInvalidFormatError: If file is not a valid PDF
            PDFExtractionTimeout: If extraction exceeds timeout
        """
        pages, _ = self.extract_text(pdf_path)
        return pages

    @with_retry_sync(max_retries=3, initial_delay=1.0)
    def extract_text(self, pdf_path: Path) -> tuple[List[PDFPage], PDFMetadata]:
        """
        Extract text and metadata from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Tuple of (list of PDFPage objects, PDFMetadata object)

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            PDFCorruptedError: If the PDF file is corrupted
            PDFEncryptedError: If the PDF file is encrypted
            PDFInvalidFormatError: If file is not a valid PDF
            PDFExtractionTimeout: If extraction exceeds timeout
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        start_time = time.time()
        try:
            pdf_doc = fitz.open(pdf_path)
            
            # Check if PDF is encrypted
            if pdf_doc.needs_pass:
                raise PDFEncryptedError(f"PDF is encrypted: {pdf_path}")
                
            # Check if PDF is valid
            if not pdf_doc.is_pdf:
                raise PDFInvalidFormatError(f"Not a valid PDF: {pdf_path}")
                
            metadata = self.extract_metadata(pdf_doc)
            pages = []
            
            logger.info(f"Starting extraction of {pdf_path} ({metadata.page_count} pages)")
            
        except fitz.FileDataError as e:
            raise PDFCorruptedError(f"PDF file is corrupted: {e}")
        except Exception as e:
            raise PDFExtractionError(f"Failed to open PDF file: {e}")
            
        # Track overall extraction time
        if time.time() - start_time > self.timeout:
            raise PDFExtractionTimeout(f"PDF extraction timed out after {self.timeout}s")

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
                         skip_existing: bool = True) -> Dict[Path, tuple[List[PDFPage], PDFMetadata]]:
        """
        Process all PDFs in the data directory or a subdirectory.
        
        Args:
            subdir: Optional subdirectory within data folder to process
            skip_existing: Skip PDFs that have already been processed
            
        Returns:
            Dictionary mapping PDF paths to tuples of (pages, metadata)
        """
        pdf_files = list_pdf_files(subdir)
        results = {}
        errors = []
        
        logger.info(f"Processing {len(pdf_files)} PDF files from {subdir or 'root'}")
        
        for i, pdf_path in enumerate(pdf_files, 1):
            try:
                pages, metadata = self.extract_text(pdf_path)
                results[pdf_path] = (pages, metadata)
                
                if self.progress_callback:
                    self.progress_callback(i, len(pdf_files))
                    
                logger.info(f"Successfully processed {pdf_path} ({metadata.page_count} pages)")
                
            except PDFExtractionError as e:
                logger.error(f"Error processing {pdf_path}: {str(e)}")
                errors.append((pdf_path, str(e)))
            except Exception as e:
                logger.exception(f"Unexpected error processing {pdf_path}")
                errors.append((pdf_path, str(e)))
        
        if errors:
            logger.warning(f"Failed to process {len(errors)} files:")
            for path, error in errors:
                logger.warning(f"- {path}: {error}")
                
        logger.info(f"Successfully processed {len(results)}/{len(pdf_files)} PDF files")
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