"""
Text chunking module that handles semantic chunking of document content.
Uses the LangChain inspired approach to split text into semantically meaningful chunks.
"""
from dataclasses import dataclass
from typing import List, Optional


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

    def create_chunks(self, 
                     text: str,
                     page_number: int,
                     metadata: Optional[dict] = None) -> List[TextChunk]:
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