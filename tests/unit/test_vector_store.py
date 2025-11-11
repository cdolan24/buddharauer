"""
Tests for the vector store implementation.

These tests verify:
1. Document addition and retrieval
2. Custom ID support
3. Metadata filtering
4. Collection management
5. Vector similarity search
6. Retry behavior
7. Error cases
8. Data persistence

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
@pytest.mark.asyncio
async def test_add_documents_with_retry(vector_store: VectorStore):
    """Test adding documents with retry functionality."""
    texts = ["Document 1", "Document 2"]
    metadata_list = [{"source": "test1"}, {"source": "test2"}]

    # Try with empty lists - should raise ValueError
    with pytest.raises(ValueError):
        await vector_store.add_documents_with_retry([], [])

    # Try with mismatched lengths - should raise ValueError
    with pytest.raises(ValueError):
        await vector_store.add_documents_with_retry(
            texts=["single doc"], 
            metadata_list=[{"source": "1"}, {"source": "2"}]
        )

    # Normal case should succeed
    ids = await vector_store.add_documents_with_retry(
        texts=texts,
        metadata_list=metadata_list
    )
    assert len(ids) == 2
    assert vector_store.get_collection_stats()["total_documents"] == 2


@pytest.mark.asyncio
async def test_search_error_cases(vector_store: VectorStore):
    """Test error cases for search functionality."""
    # Empty query list should return empty results
    results = await vector_store.search(query_texts=[])
    assert not results["ids"]
    assert not results["documents"]
    assert not results["metadatas"]
    assert not results["distances"]

    # Search with no documents should return empty results
    results = await vector_store.search(
        query_texts=["test query"],
        where={"nonexistent": "filter"}
    )
    # ChromaDB API returns one list per query, so with 1 query we get [[]]
    assert len(results["ids"]) == 1  # One result list
    assert len(results["ids"][0]) == 0  # That list is empty

    # Add some documents and test filtering
    await vector_store.add_documents(
        texts=["Document 1", "Document 2"],
        metadata_list=[
            {"source": "src1"},
            {"source": "src2"}
        ]
    )

    # Search with filter that matches no documents
    results = await vector_store.search(
        query_texts=["document"],
        where={"source": "nonexistent"}
    )
    assert len(results["ids"]) == 1
    assert not results["ids"][0]  # Empty list for this query


@pytest.mark.asyncio
async def test_persistence(vector_store: VectorStore):
    """Test document persistence between store instances."""
    # Add documents
    await vector_store.add_documents(
        texts=["Test document"],
        metadata_list=[{"source": "test"}]
    )

    # Create new instance with same directory
    new_store = VectorStore(
        persist_directory=vector_store.persist_directory
    )

    # Should have same documents
    assert new_store.get_collection_stats()["total_documents"] == 1

    # Search should work in new instance
    results = await new_store.search(
        query_texts=["test"],
        n_results=1
    )
    assert len(results["ids"][0]) == 1


def test_delete_collection(vector_store: VectorStore):
    """Test deleting the collection."""
    vector_store.delete_collection()
    # Creating a new store should work after deletion
    new_store = VectorStore(
        persist_directory=vector_store.persist_directory
    )
    assert new_store.get_collection_stats()["total_documents"] == 0


def test_cosine_similarity_with_lists():
    """Test cosine similarity function with list inputs (lines 70-73)."""
    from src.database.vector_store import cosine_similarity

    # Test with list inputs (triggers lines 70-73)
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [2.0, 4.0, 6.0]

    similarity = cosine_similarity(vec1, vec2)
    assert abs(similarity - 1.0) < 0.001  # Vectors in same direction

    # Test with orthogonal vectors
    vec3 = [1.0, 0.0, 0.0]
    vec4 = [0.0, 1.0, 0.0]
    similarity = cosine_similarity(vec3, vec4)
    assert abs(similarity - 0.0) < 0.001  # Orthogonal vectors


@pytest.mark.asyncio
async def test_add_documents_invalid_ids_length(vector_store: VectorStore):
    """Test validation of ids length mismatch (line 152)."""
    texts = ["Text one", "Text two"]
    metadata_list = [{"source": "test1"}, {"source": "test2"}]

    # Invalid: ids length doesn't match texts length
    with pytest.raises(ValueError, match="ids must have same length"):
        await vector_store.add_documents(
            texts=texts,
            metadata_list=metadata_list,
            ids=["id1"]  # Only 1 id for 2 texts
        )


@pytest.mark.asyncio
async def test_delete_collection_with_existing_data(vector_store: VectorStore):
    """Test delete_collection when collection file exists (line 357)."""
    # Add documents to create collection file
    await vector_store.add_documents(
        texts=["Test document"],
        metadata_list=[{"source": "test"}]
    )

    # Verify collection file exists
    assert vector_store.collection_path.exists()

    # Delete collection (should remove file)
    vector_store.delete_collection()

    # Verify file is gone and in-memory data cleared
    assert not vector_store.collection_path.exists()
    assert len(vector_store.documents) == 0
    assert vector_store.get_collection_stats()["total_documents"] == 0


@pytest.mark.asyncio
async def test_add_documents_with_retry_error_logging(vector_store: VectorStore):
    """Test error handling and logging in add_documents_with_retry (lines 417-419)."""
    from unittest.mock import patch, AsyncMock

    # Mock add_documents to raise an exception
    with patch.object(vector_store, 'add_documents', new_callable=AsyncMock) as mock_add:
        mock_add.side_effect = Exception("Test error")

        # Should raise the exception and log error
        with pytest.raises(Exception, match="Test error"):
            await vector_store.add_documents_with_retry(
                texts=["Test"],
                metadata_list=[{"source": "test"}]
            )