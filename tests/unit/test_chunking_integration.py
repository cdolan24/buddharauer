"""
Tests for the integration between PDF extraction and chunking.
"""
import pytest
from pathlib import Path
from src.pipeline.chunker import SemanticChunker, ChunkPipeline, TextChunk
from src.pipeline.pdf_extractor import PDFExtractor


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a sample PDF for testing."""
    # This is handled by conftest.py fixture
    return Path("tests/data/test.pdf")


@pytest.fixture
def chunker():
    """Create a semantic chunker instance."""
    return SemanticChunker(chunk_size=200, chunk_overlap=20)


@pytest.fixture
def pipeline(chunker):
    """Create a chunk pipeline instance."""
    return ChunkPipeline(chunker, optimize_chunks=True)


def test_process_pdf_creates_chunks(chunker, sample_pdf_path):
    """Test that processing a PDF creates the expected chunks."""
    chunks = chunker.process_pdf(sample_pdf_path)
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert isinstance(chunk, TextChunk)
        assert chunk.text.strip()
        assert chunk.page_number > 0
        assert chunk.metadata['source'] == str(sample_pdf_path)
        assert 'title' in chunk.metadata
        assert 'author' in chunk.metadata
        assert 'is_scanned' in chunk.metadata


def test_chunk_size_optimization(chunker, sample_pdf_path):
    """Test that chunk size optimization works."""
    # Process with default size
    original_size = chunker.chunk_size
    chunks_before = chunker.process_pdf(sample_pdf_path, optimize_chunks=False)
    
    # Process with optimization
    chunks_after = chunker.process_pdf(sample_pdf_path, optimize_chunks=True)
    
    assert chunker.chunk_size != original_size
    assert len(chunks_after) > 0


def test_pipeline_processes_multiple_files(pipeline, tmp_path):
    """Test that pipeline can process multiple PDFs."""
    # Create test directory with sample PDFs
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    
    # Process directory
    results = pipeline.process_directory(pdf_dir)
    
    assert isinstance(results, dict)
    assert pipeline.get_stats()['files_processed'] >= 0


def test_chunk_metadata_preservation(chunker, sample_pdf_path):
    """Test that metadata is preserved through the chunking process."""
    # Extract original metadata
    extractor = PDFExtractor()
    metadata = extractor.extract_metadata(sample_pdf_path)
    
    # Process PDF into chunks
    chunks = chunker.process_pdf(sample_pdf_path)
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.metadata['title'] == metadata.title
        assert chunk.metadata['author'] == metadata.author
        assert chunk.metadata['total_pages'] == metadata.page_count
        assert 'creation_date' in chunk.metadata


def test_chunk_overlap(chunker):
    """Test that chunk overlap is working correctly."""
    text = "This is sentence one. This is sentence two. " * 10
    chunks = chunker.create_chunks(text, page_number=1)
    
    # Check consecutive chunks for overlap
    for i in range(len(chunks) - 1):
        current = chunks[i].text
        next_chunk = chunks[i + 1].text
        
        # The end of the current chunk should appear at the start of the next
        assert current[-chunker.chunk_overlap:] in next_chunk


def test_error_handling(pipeline, tmp_path):
    """Test that pipeline handles errors gracefully."""
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_bytes(b"Not a PDF file")
    
    # Should not raise exception
    results = pipeline.process_directory(tmp_path)
    
    assert str(bad_pdf) not in results
    assert pipeline.get_stats()['files_processed'] == 0


def test_stats_tracking(pipeline, tmp_path):
    """Test that pipeline statistics are tracked correctly."""
    # Process some files
    pipeline.process_directory(tmp_path)
    
    # Check stats
    stats = pipeline.get_stats()
    assert 'files_processed' in stats
    assert 'total_chunks' in stats
    assert 'avg_chunks_per_file' in stats
    assert isinstance(stats['files_processed'], int)
    assert isinstance(stats['total_chunks'], int)