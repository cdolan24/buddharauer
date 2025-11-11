"""Tests for pipeline recovery functionality."""
import asyncio
import json
from pathlib import Path
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.pipeline.recovery import RecoveryManager, RecoveryState, with_retry
from src.pipeline.orchestrator import PipelineOrchestrator, ProcessingStats
from src.pipeline.chunker import ChunkPipeline, TextChunk
from src.database.vector_store import VectorStore


def test_recovery_state_serialization():
    """Test RecoveryState serialization/deserialization."""
    state = RecoveryState(
        operation_id="test_op_1",
        start_time=1234567890.0,
        operation_type="process_pdf",
        input_data={"pdf_path": "/test/doc.pdf"},
        status="started"
    )
    
    # Test to_dict
    state_dict = state.to_dict()
    assert state_dict["operation_id"] == "test_op_1"
    assert state_dict["operation_type"] == "process_pdf"
    assert state_dict["status"] == "started"
    
    # Test from_dict
    reconstructed = RecoveryState.from_dict(state_dict)
    assert reconstructed.operation_id == state.operation_id
    assert reconstructed.start_time == state.start_time
    assert reconstructed.operation_type == state.operation_type
    assert reconstructed.input_data == state.input_data
    assert reconstructed.status == state.status


@pytest.fixture
def recovery_manager(tmp_path):
    """Create a RecoveryManager instance."""
    return RecoveryManager(tmp_path)


def test_recovery_manager_operations(recovery_manager):
    """Test RecoveryManager operation tracking."""
    # Start operation
    state = recovery_manager.start_operation(
        "test_op",
        {"test_param": "test_value"}
    )
    assert state.operation_id in recovery_manager.active_operations
    assert state.status == "started"
    
    # Update operation
    recovery_manager.update_operation(
        state.operation_id,
        "in_progress"
    )
    updated = recovery_manager.active_operations[state.operation_id]
    assert updated.status == "in_progress"
    
    # Complete operation
    recovery_manager.update_operation(
        state.operation_id,
        "completed"
    )
    assert state.operation_id not in recovery_manager.active_operations


@pytest.mark.asyncio
async def test_retry_decorator():
    """Test retry decorator functionality."""
    mock_fn = AsyncMock()
    mock_fn.side_effect = [ValueError(), ValueError(), "success"]
    
    @with_retry(max_retries=3, initial_delay=0.1)
    async def test_fn():
        return await mock_fn()
    
    result = await test_fn()
    assert result == "success"
    assert mock_fn.call_count == 3


@pytest.fixture
def mock_chunk_pipeline():
    """Create a mock ChunkPipeline."""
    pipeline = Mock(spec=ChunkPipeline)
    pipeline.process_file.return_value = [
        TextChunk("test text", 1, 0, 1, {"test": "metadata"})
    ]
    return pipeline


@pytest.fixture
def mock_vector_store():
    """Create a mock VectorStore."""
    store = Mock(spec=VectorStore)
    store.add_documents = AsyncMock(return_value=["doc1"])
    return store


@pytest.mark.asyncio
async def test_orchestrator_recovery(tmp_path, mock_chunk_pipeline, mock_vector_store):
    """Test orchestrator recovery functionality."""
    # Create test PDF
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    test_pdf = pdf_dir / "test.pdf"
    test_pdf.write_bytes(b"dummy pdf")
    
    # Create orchestrator with recovery
    recovery_dir = tmp_path / "recovery"
    orchestrator = PipelineOrchestrator(
        mock_chunk_pipeline,
        mock_vector_store,
        state_dir=recovery_dir
    )
    
    # Create incomplete operation (in_progress state so it will be retried)
    state = orchestrator.recovery.start_operation(
        "process_pdf",
        {"pdf_path": str(test_pdf)}
    )
    # Leave the operation in "in_progress" state (don't mark as failed)
    # This simulates an interrupted operation that needs recovery

    # Process directory - should retry the incomplete operation
    stats = await orchestrator.process_directory(pdf_dir)

    # Verify recovery
    assert stats.retry_successes == 1, f"Expected 1 retry success, got {stats.retry_successes}"
    assert stats.successful_files == 1, f"Expected 1 successful file, got {stats.successful_files}"
    assert stats.failed_files == 0, f"Expected 0 failed files, got {stats.failed_files}"
    assert mock_chunk_pipeline.process_file.call_count == 1
    assert mock_vector_store.add_documents.call_count == 1


@pytest.mark.asyncio
async def test_orchestrator_duplicate_prevention(
    tmp_path,
    mock_chunk_pipeline,
    mock_vector_store
):
    """Test prevention of duplicate processing."""
    # Create test PDF
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    test_pdf = pdf_dir / "test.pdf"
    test_pdf.write_bytes(b"dummy pdf")
    
    # Create orchestrator
    orchestrator = PipelineOrchestrator(
        mock_chunk_pipeline,
        mock_vector_store,
        state_dir=tmp_path / "recovery"
    )
    
    # Process same file twice
    await orchestrator.process_pdf(test_pdf)
    await orchestrator.process_pdf(test_pdf)
    
    # Verify single processing
    assert mock_chunk_pipeline.process_file.call_count == 1
    assert mock_vector_store.add_documents.call_count == 1


@pytest.mark.asyncio
async def test_orchestrator_vector_store_retry(
    tmp_path,
    mock_chunk_pipeline
):
    """Test vector store operation retries."""
    # Mock vector store with temporary failure
    mock_store = Mock(spec=VectorStore)
    mock_store.add_documents = AsyncMock(
        side_effect=[ValueError(), ValueError(), ["doc1"]]
    )
    
    # Create test PDF
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    test_pdf = pdf_dir / "test.pdf"
    test_pdf.write_bytes(b"dummy pdf")
    
    # Create orchestrator
    orchestrator = PipelineOrchestrator(
        mock_chunk_pipeline,
        mock_store,
        state_dir=tmp_path / "recovery"
    )
    
    # Process file
    success = await orchestrator.process_pdf(test_pdf)
    
    # Verify retries and success
    assert success is True
    assert mock_store.add_documents.call_count == 3