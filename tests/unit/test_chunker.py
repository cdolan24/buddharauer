"""Tests for semantic chunking module."""
import pytest
from src.pipeline.chunker import SemanticChunker, TextChunk, get_optimal_chunk_size

SAMPLE_TEXT = """
This is the first paragraph.
It has multiple sentences.

This is the second paragraph.
It also has multiple lines.
And more sentences.

This is the third paragraph.
Short and sweet.
"""

def test_basic_chunking():
    """Test basic text chunking functionality."""
    chunker = SemanticChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.create_chunks(SAMPLE_TEXT, page_number=1)
    
    assert len(chunks) > 0
    assert all(isinstance(chunk, TextChunk) for chunk in chunks)
    assert all(len(chunk.text) <= 100 for chunk in chunks)

def test_chunk_metadata():
    """Test that chunks contain correct metadata."""
    metadata = {"source": "test", "language": "en"}
    chunker = SemanticChunker(chunk_size=100)
    chunks = chunker.create_chunks(SAMPLE_TEXT, page_number=1, metadata=metadata)
    
    for chunk in chunks:
        assert chunk.metadata["source"] == "test"
        assert chunk.metadata["language"] == "en"
        assert "chunk_size" in chunk.metadata
        assert chunk.page_number == 1
        assert isinstance(chunk.chunk_index, int)
        assert chunk.total_chunks == len(chunks)

def test_chunk_overlap():
    """Test that chunks overlap correctly."""
    chunker = SemanticChunker(chunk_size=50, chunk_overlap=10)
    chunks = chunker.create_chunks(SAMPLE_TEXT, page_number=1)
    
    # Check that adjacent chunks have overlapping content
    if len(chunks) > 1:
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1].text
            current_chunk = chunks[i].text
            # The end of the previous chunk should appear at the start of the current chunk
            assert prev_chunk[-10:] in current_chunk

def test_invalid_parameters():
    """Test that invalid parameters raise appropriate errors."""
    with pytest.raises(ValueError):
        SemanticChunker(chunk_size=0)
    
    with pytest.raises(ValueError):
        SemanticChunker(chunk_size=100, chunk_overlap=200)

def test_optimal_chunk_size():
    """Test optimal chunk size calculation."""
    size = get_optimal_chunk_size(SAMPLE_TEXT, target_chunks=2)
    assert 100 <= size <= 2000
    
    # Test with constraints
    size = get_optimal_chunk_size(SAMPLE_TEXT, target_chunks=2, min_size=500)
    assert size >= 500
    
    size = get_optimal_chunk_size(SAMPLE_TEXT, target_chunks=2, max_size=300)
    assert size <= 300