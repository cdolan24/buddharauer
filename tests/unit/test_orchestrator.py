"""Tests for the pipeline orchestrator."""
import pytest
from pathlib import Path
import asyncio

from src.pipeline.orchestrator import PipelineOrchestrator, ProcessingStats
from src.pipeline.chunker import ChunkPipeline, SemanticChunker
from src.database.vector_store import VectorStore


@pytest.fixture
def test_files(tmp_path):
    """Create test PDF files."""
    # Create sample PDFs
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    
    # Create a few dummy PDFs
    for i in range(3):
        pdf_path = pdf_dir / f"test{i}.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")  # Minimal PDF header
        
    return pdf_dir


@pytest.fixture
def chunker():
    """Create a semantic chunker."""
    return SemanticChunker(chunk_size=200, chunk_overlap=20)


@pytest.fixture
def chunk_pipeline(chunker):
    """Create a chunk pipeline."""
    return ChunkPipeline(chunker, optimize_chunks=True)


@pytest.fixture
def vector_store(tmp_path):
    """Create a vector store."""
    return VectorStore(
        persist_directory=tmp_path / "vector_db",
        collection_name="test"
    )


@pytest.fixture
def orchestrator(chunk_pipeline, vector_store):
    """Create a pipeline orchestrator."""
    return PipelineOrchestrator(
        chunk_pipeline=chunk_pipeline,
        vector_store=vector_store,
        batch_size=2
    )


@pytest.mark.asyncio
async def test_process_pdf(orchestrator, test_files):
    """Test processing a single PDF."""
    pdf_path = next(test_files.glob("*.pdf"))
    success = await orchestrator.process_pdf(pdf_path)
    
    assert success
    assert orchestrator.get_stats().successful_files == 1
    assert orchestrator.get_stats().failed_files == 0


@pytest.mark.asyncio
async def test_process_directory(orchestrator, test_files):
    """Test processing a directory of PDFs."""
    stats = await orchestrator.process_directory(test_files)
    
    assert isinstance(stats, ProcessingStats)
    assert stats.total_files == 3
    assert stats.successful_files + stats.failed_files == 3
    assert stats.processing_time > 0


@pytest.mark.asyncio
async def test_error_handling(orchestrator, test_files):
    """Test handling of corrupted PDFs."""
    # Create a corrupted PDF
    bad_pdf = test_files / "corrupted.pdf"
    bad_pdf.write_bytes(b"Not a PDF file")
    
    success = await orchestrator.process_pdf(bad_pdf)
    
    assert not success
    assert orchestrator.get_stats().failed_files == 1
    assert str(bad_pdf) in orchestrator.get_stats().errors


@pytest.mark.asyncio
async def test_batched_processing(orchestrator, test_files):
    """Test that documents are processed in batches."""
    stats = await orchestrator.process_directory(test_files)
    
    # Since batch_size=2, chunks should be processed in batches of 2
    assert stats.total_chunks > 0