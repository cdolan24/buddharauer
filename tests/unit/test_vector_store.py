"""
Tests for the vector store implementation.

These tests verify:
1. Document addition and retrieval
2. Custom ID support
3. Metadata filtering
4. Collection management
5. Vector similarity search

The tests use a temporary directory for storage to avoid affecting
the main vector store data.

Note: These tests require the Ollama service to be running with
the nomic-embed-text model available.
"""
import pytest
import tempfile
from pathlib import Path
from typing import List, Dict

from src.database.vector_store import VectorStore, Document


@pytest.fixture
def vector_store():
    """Create a temporary vector store for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        store = VectorStore(persist_directory=temp_dir)
        yield store


@pytest.mark.asyncio
async def test_add_and_search_documents(vector_store: VectorStore):
    """Test adding documents and searching them."""
    # Test data
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "A quick brown dog jumps over the lazy fox.",
        "The lazy fox and dog are friends."
    ]
    metadata_list = [
        {"page": 1, "source": "test1"},
        {"page": 1, "source": "test2"},
        {"page": 2, "source": "test1"}
    ]
    
    # Add documents
    ids = await vector_store.add_documents(texts, metadata_list)
    assert len(ids) == 3
    
    # Check collection stats
    stats = vector_store.get_collection_stats()
    assert stats["total_documents"] == 3
    
    # Search similar documents
    results = await vector_store.search(
        query_texts=["quick brown animal jumps"],
        n_results=2
    )
    
    # Verify results
    assert len(results["ids"][0]) == 2  # Two results
    assert results["documents"]  # Should contain matching documents
    assert results["metadatas"]  # Should contain metadata


@pytest.mark.asyncio
async def test_add_with_custom_ids(vector_store: VectorStore):
    """Test adding documents with custom IDs."""
    texts = ["Text one", "Text two"]
    metadata_list = [
        {"source": "test1"},
        {"source": "test2"}
    ]
    custom_ids = ["id1", "id2"]
    
    ids = await vector_store.add_documents(
        texts=texts,
        metadata_list=metadata_list,
        ids=custom_ids
    )
    
    assert ids == custom_ids
    stats = vector_store.get_collection_stats()
    assert stats["total_documents"] == 2


@pytest.mark.asyncio
async def test_search_with_filters(vector_store: VectorStore):
    """Test searching with metadata filters."""
    # Add test documents
    texts = [
        "Document from source one",
        "Document from source two",
        "Another document from source one"
    ]
    metadata_list = [
        {"source": "source1", "page": 1},
        {"source": "source2", "page": 1},
        {"source": "source1", "page": 2}
    ]
    
    await vector_store.add_documents(texts, metadata_list)

    # Search with metadata filter
    results = await vector_store.search(
        query_texts=["document"],
        n_results=5,
        where={"source": "source1"}
    )

    # Should only return documents from source1
    assert len(results["ids"][0]) == 2
    for metadata in results["metadatas"][0]:
        assert metadata["source"] == "source1"
def test_delete_collection(vector_store: VectorStore):
    """Test deleting the collection."""
    vector_store.delete_collection()
    # Creating a new store should work after deletion
    new_store = VectorStore(
        persist_directory=vector_store.persist_directory
    )
    assert new_store.get_collection_stats()["total_documents"] == 0