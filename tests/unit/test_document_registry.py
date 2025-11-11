"""
Tests for the document registry module.

These tests verify:
1. Database initialization
2. Document addition and retrieval
3. Status updates
4. Querying by status
5. Statistics and aggregations
6. Error handling
"""

import pytest
import pytest_asyncio
import tempfile
import asyncio
from pathlib import Path

from src.database.document_registry import DocumentRegistry, DocumentRecord


@pytest_asyncio.fixture
async def registry():
    """Create a temporary document registry for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_documents.db"
        reg = DocumentRegistry(db_path)
        await reg.initialize()
        yield reg


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a temporary test PDF file."""
    pdf_path = tmp_path / "test_document.pdf"
    # Write some dummy content
    pdf_path.write_bytes(b"%PDF-1.4\nTest content")
    return pdf_path


@pytest.mark.asyncio
async def test_initialize_registry(registry):
    """Test database initialization."""
    # Should already be initialized by fixture
    # Just verify we can query it
    docs = await registry.list_all()
    assert docs == []


@pytest.mark.asyncio
async def test_add_document(registry, sample_pdf):
    """Test adding a document to registry."""
    doc_id = await registry.add_document(
        filepath=sample_pdf,
        filename="test_document.pdf",
        file_size=1024,
        pages=5
    )

    assert doc_id is not None
    assert len(doc_id) == 64  # SHA256 hash length

    # Retrieve and verify
    doc = await registry.get_by_id(doc_id)
    assert doc is not None
    assert doc.filename == "test_document.pdf"
    assert doc.status == "pending"
    assert doc.pages == 5
    assert doc.file_size_bytes == 1024


@pytest.mark.asyncio
async def test_add_duplicate_document(registry, sample_pdf):
    """Test that adding same document twice raises error."""
    # Add once
    await registry.add_document(
        filepath=sample_pdf,
        filename="test.pdf",
        file_size=100
    )

    # Try to add again - should raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        await registry.add_document(
            filepath=sample_pdf,
            filename="test.pdf",
            file_size=100
        )


@pytest.mark.asyncio
async def test_update_status(registry, sample_pdf):
    """Test updating document status."""
    doc_id = await registry.add_document(
        filepath=sample_pdf,
        filename="test.pdf",
        file_size=100
    )

    # Update to processing
    await registry.update_status(doc_id, "processing")
    doc = await registry.get_by_id(doc_id)
    assert doc.status == "processing"
    assert doc.processing_start is not None

    # Update to failed with error
    await registry.update_status(doc_id, "failed", error_message="Test error")
    doc = await registry.get_by_id(doc_id)
    assert doc.status == "failed"
    assert doc.error_message == "Test error"


@pytest.mark.asyncio
async def test_mark_completed(registry, sample_pdf):
    """Test marking document as completed."""
    doc_id = await registry.add_document(
        filepath=sample_pdf,
        filename="test.pdf",
        file_size=100
    )

    # Start processing
    await registry.update_status(doc_id, "processing")

    # Mark as completed
    await registry.mark_completed(doc_id, chunk_count=50, token_count=1000)

    doc = await registry.get_by_id(doc_id)
    assert doc.status == "completed"
    assert doc.chunk_count == 50
    assert doc.token_count == 1000
    assert doc.processing_end is not None
    assert doc.processing_time_seconds is not None
    assert doc.processing_time_seconds >= 0


@pytest.mark.asyncio
async def test_get_by_status(registry, sample_pdf):
    """Test querying documents by status."""
    # Add multiple documents with different statuses
    doc1_id = await registry.add_document(
        filepath=sample_pdf,
        filename="pending.pdf",
        file_size=100
    )

    # Create another temp file for second document
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4\nDifferent content")
        temp_path = Path(f.name)

    try:
        doc2_id = await registry.add_document(
            filepath=temp_path,
            filename="completed.pdf",
            file_size=200
        )

        # Set different statuses
        await registry.update_status(doc2_id, "processing")
        await registry.mark_completed(doc2_id, chunk_count=10, token_count=100)

        # Query by status
        pending_docs = await registry.get_by_status("pending")
        completed_docs = await registry.get_by_status("completed")

        assert len(pending_docs) == 1
        assert pending_docs[0].filename == "pending.pdf"

        assert len(completed_docs) == 1
        assert completed_docs[0].filename == "completed.pdf"
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_list_all_with_pagination(registry, sample_pdf):
    """Test listing all documents with pagination."""
    # Add a document
    await registry.add_document(
        filepath=sample_pdf,
        filename="test.pdf",
        file_size=100
    )

    # List all
    all_docs = await registry.list_all()
    assert len(all_docs) == 1

    # List with limit
    limited = await registry.list_all(limit=1, offset=0)
    assert len(limited) == 1

    # List with offset beyond data
    empty = await registry.list_all(limit=10, offset=10)
    assert len(empty) == 0


@pytest.mark.asyncio
async def test_count_by_status(registry, sample_pdf):
    """Test counting documents by status."""
    # Initially empty
    counts = await registry.count_by_status()
    assert counts == {}

    # Add documents
    doc_id = await registry.add_document(
        filepath=sample_pdf,
        filename="test.pdf",
        file_size=100
    )

    counts = await registry.count_by_status()
    assert counts.get("pending", 0) == 1

    # Update status
    await registry.update_status(doc_id, "processing")
    counts = await registry.count_by_status()
    assert counts.get("pending", 0) == 0
    assert counts.get("processing", 0) == 1


@pytest.mark.asyncio
async def test_delete_document(registry, sample_pdf):
    """Test deleting a document."""
    doc_id = await registry.add_document(
        filepath=sample_pdf,
        filename="test.pdf",
        file_size=100
    )

    # Verify it exists
    assert await registry.get_by_id(doc_id) is not None

    # Delete it
    await registry.delete_document(doc_id)

    # Verify it's gone
    assert await registry.get_by_id(doc_id) is None


@pytest.mark.asyncio
async def test_get_statistics(registry, sample_pdf):
    """Test getting registry statistics."""
    # Initially no stats
    stats = await registry.get_statistics()
    assert stats["total_documents"] == 0

    # Add and complete a document
    doc_id = await registry.add_document(
        filepath=sample_pdf,
        filename="test.pdf",
        file_size=100,
        pages=5
    )
    await registry.update_status(doc_id, "processing")
    await registry.mark_completed(doc_id, chunk_count=25, token_count=500)

    # Check stats
    stats = await registry.get_statistics()
    assert stats["total_documents"] == 1
    assert stats["total_chunks"] == 25
    assert stats["total_tokens"] == 500
    assert stats["avg_processing_time"] >= 0
    assert "completed" in stats["status_counts"]
    assert stats["status_counts"]["completed"] == 1


@pytest.mark.asyncio
async def test_file_hash_consistency(registry, sample_pdf):
    """Test that file hash is consistent."""
    hash1 = DocumentRegistry.compute_file_hash(sample_pdf)
    hash2 = DocumentRegistry.compute_file_hash(sample_pdf)

    # Same file should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256
