"""
Text chunking module that handles semantic chunking of document content.
Uses the LangChain inspired approach to split text into semantically meaningful chunks.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

from .pdf_extractor import PDFExtractor, PDFPage, PDFMetadata
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """A semantically meaningful chunk of text."""
    text: str
    page_number: int
    chunk_index: int
    total_chunks: int
    metadata: dict


class SemanticChunker:
    """Handles splitting text into semantically meaningful chunks."""

    def __init__(self, 
                 chunk_size: int = 500,
                 chunk_overlap: int = 50,
                 length_function=len):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            length_function: Function to measure text length (default: len)
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
            
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function

    def _split_text(self, text: str) -> List[str]:
        """
        Split text into chunks based on semantic boundaries.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # Start with basic paragraph splits
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            paragraph_length = self.length_function(paragraph)
            
            if current_length + paragraph_length <= self.chunk_size:
                current_chunk.append(paragraph)
                current_length += paragraph_length
            else:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_length = paragraph_length
                
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
        # Add overlapping content
        if self.chunk_overlap > 0 and len(chunks) > 1:
            overlapped_chunks = []
            
            for i in range(len(chunks)):
                if i == 0:
                    overlapped_chunks.append(chunks[i])
                else:
                    # Add overlap from previous chunk
                    prev_chunk = chunks[i-1]
                    overlap = prev_chunk[-self.chunk_overlap:]
                    overlapped_chunks.append(overlap + chunks[i])
                    
            chunks = overlapped_chunks
            
        return chunks

    def process_pdf(self, 
                   pdf_path: Path,
                   optimize_chunks: bool = True,
                   target_chunks_per_page: int = 5) -> List[TextChunk]:
        """
        Process a PDF file and create semantic chunks.
        
        Args:
            pdf_path: Path to PDF file
            optimize_chunks: Whether to optimize chunk size based on content
            target_chunks_per_page: Target number of chunks per page when optimizing
            
        Returns:
            List of TextChunk objects with metadata
        """
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract text and metadata from PDF
        extractor = PDFExtractor()
        metadata = extractor.extract_metadata(pdf_path)
        pages = extractor.extract_pages(pdf_path)
        
        # Optimize chunk size if requested
        if optimize_chunks:
            # Sample first few pages for optimization
            sample_text = "\n\n".join(page.text for page in pages[:3])
            optimal_size = get_optimal_chunk_size(
                sample_text,
                target_chunks=target_chunks_per_page * len(pages[:3])
            )
            logger.info(f"Optimized chunk size: {optimal_size}")
            self.chunk_size = optimal_size
        
        # Process each page
        all_chunks = []
        
        for page in pages:
            # Create base metadata
            page_metadata = {
                'source': str(pdf_path),
                'page': page.number,
                'total_pages': metadata.page_count,
                'is_scanned': page.is_scanned,
                'title': metadata.title,
                'author': metadata.author,
                'creation_date': metadata.creation_date.isoformat() if metadata.creation_date else None,
            }
            
            # Create chunks for this page
            page_chunks = self.create_chunks(
                text=page.text,
                page_number=page.number,
                metadata=page_metadata
            )
            
            all_chunks.extend(page_chunks)
            
        logger.info(f"Created {len(all_chunks)} chunks from {metadata.page_count} pages")
        return all_chunks

    def create_chunks(self, 
                     text: str,
                     page_number: int,
                     metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """
        Create semantic chunks from text with metadata.
        
        Args:
            text: Text to chunk
            page_number: Page number this text came from
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of TextChunk objects
        """
        chunks = self._split_text(text)
        
        chunk_objects = []
        metadata = metadata or {}
        
        for i, chunk_text in enumerate(chunks):
            chunk = TextChunk(
                text=chunk_text,
                page_number=page_number,
                chunk_index=i,
                total_chunks=len(chunks),
                metadata={
                    **metadata,
                    'chunk_size': self.chunk_size,
                    'chunk_overlap': self.chunk_overlap,
                }
            )
            chunk_objects.append(chunk)
            
        return chunk_objects


def get_optimal_chunk_size(text: str,
                          target_chunks: int = 10,
                          min_size: int = 100,
                          max_size: int = 2000) -> int:
    """
    Calculate optimal chunk size to get approximately target_chunks.
    
    Args:
        text: Sample text to analyze
        target_chunks: Desired number of chunks
        min_size: Minimum chunk size to consider
        max_size: Maximum chunk size to consider
        
    Returns:
        Recommended chunk size
    """
    text_length = len(text)
    
    # Aim for chunk size that would give us target number of chunks
    chunk_size = text_length // target_chunks
    
    # Constrain to min/max
    chunk_size = max(min_size, min(chunk_size, max_size))
    
    return chunk_size


class ChunkPipeline:
    """Pipeline for processing PDFs into semantic chunks."""
    
    def __init__(self,
                 chunker: SemanticChunker,
                 optimize_chunks: bool = True,
                 target_chunks_per_page: int = 5):
        """
        Initialize the pipeline.
        
        Args:
            chunker: SemanticChunker instance
            optimize_chunks: Whether to optimize chunk size based on content
            target_chunks_per_page: Target number of chunks per page when optimizing
        """
        self.chunker = chunker
        self.optimize_chunks = optimize_chunks
        self.target_chunks_per_page = target_chunks_per_page
        self.total_processed = 0
        self.total_chunks = 0
        
    def process_file(self, pdf_path: Path) -> List[TextChunk]:
        """Process a single PDF file."""
        chunks = self.chunker.process_pdf(
            pdf_path,
            optimize_chunks=self.optimize_chunks,
            target_chunks_per_page=self.target_chunks_per_page
        )
        self.total_processed += 1
        self.total_chunks += len(chunks)
        return chunks
        
    def process_directory(self, dir_path: Path) -> Dict[str, List[TextChunk]]:
        """Process all PDFs in a directory."""
        results = {}
        for pdf_path in dir_path.glob('**/*.pdf'):
            try:
                chunks = self.process_file(pdf_path)
                results[str(pdf_path)] = chunks
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {str(e)}")
                continue
        return results
        
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return {
            'files_processed': self.total_processed,
            'total_chunks': self.total_chunks,
            'avg_chunks_per_file': self.total_chunks // max(1, self.total_processed)
        }