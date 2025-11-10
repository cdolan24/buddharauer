"""
Custom exceptions for the PDF extraction pipeline.
"""

class PDFExtractionError(Exception):
    """Base class for PDF extraction errors."""
    pass

class PDFCorruptedError(PDFExtractionError):
    """Raised when a PDF file is corrupted."""
    pass

class PDFEncryptedError(PDFExtractionError):
    """Raised when a PDF file is encrypted."""
    pass

class PDFInvalidFormatError(PDFExtractionError):
    """Raised when a file is not a valid PDF."""
    pass

class PDFExtractionTimeout(PDFExtractionError):
    """Raised when PDF extraction times out."""
    pass