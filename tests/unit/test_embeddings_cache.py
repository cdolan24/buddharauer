"""Tests for the embeddings cache module."""
import pytest
from pathlib import Path
import json
import asyncio
from src.pipeline.embeddings_cache import EmbeddingsCache


@pytest.fixture
def cache_dir(tmp_path):
    """Create a temporary directory for cache testing."""
    return tmp_path / "embeddings_cache"


@pytest.fixture
def embeddings_cache(cache_dir):
    """Create a test embeddings cache instance."""
    return EmbeddingsCache(cache_dir)


@pytest.mark.asyncio
async def test_cache_operations(embeddings_cache):
    """Test basic cache operations."""
    text = "test text"
    embedding = [0.1, 0.2, 0.3]
    
    # Initial get should return None
    assert await embeddings_cache.get(text) is None
    
    # Put and retrieve
    await embeddings_cache.put(text, embedding)
    cached = await embeddings_cache.get(text)
    assert cached == embedding


@pytest.mark.asyncio
async def test_batch_operations(embeddings_cache):
    """Test batch cache operations."""
    texts = ["text1", "text2", "text3"]
    embeddings = {
        "text1": [0.1],
        "text2": [0.2],
        "text3": [0.3]
    }
    
    # Put batch
    await embeddings_cache.put_batch(embeddings)
    
    # Get batch
    cached = await embeddings_cache.get_batch(texts)
    assert cached == embeddings
    
    # Get uncached
    uncached = embeddings_cache.get_uncached_texts(texts + ["text4"])
    assert uncached == {"text4"}


@pytest.mark.asyncio
async def test_concurrent_writes(embeddings_cache):
    """Test concurrent cache writes."""
    text = "test text"
    embedding1 = [0.1]
    embedding2 = [0.2]
    
    # Simulate concurrent writes
    await asyncio.gather(
        embeddings_cache.put(text, embedding1),
        embeddings_cache.put(text, embedding2)
    )
    
    # Should have one of the embeddings
    cached = await embeddings_cache.get(text)
    assert cached in (embedding1, embedding2)


@pytest.mark.asyncio
async def test_corrupted_cache(embeddings_cache, cache_dir):
    """Test handling of corrupted cache files."""
    text = "test text"
    embedding = [0.1, 0.2, 0.3]
    
    # Create corrupted cache file
    cache_path = embeddings_cache._get_cache_path(text)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("invalid json")
    
    # Should handle corrupted file
    assert await embeddings_cache.get(text) is None
    
    # Should be able to write new data
    await embeddings_cache.put(text, embedding)
    assert await embeddings_cache.get(text) == embedding


@pytest.mark.asyncio
async def test_cache_metadata(embeddings_cache):
    """Test cache metadata storage."""
    text = "test text"
    embedding = [0.1, 0.2, 0.3]
    
    await embeddings_cache.put(text, embedding)
    
    # Read raw cache file
    cache_path = embeddings_cache._get_cache_path(text)
    data = json.loads(cache_path.read_text())
    
    assert data["text"] == text
    assert data["embedding"] == embedding
    assert "timestamp" in data


def test_cache_directory_creation(cache_dir):
    """Test cache directory is created if it doesn't exist."""
    assert not cache_dir.exists()
    EmbeddingsCache(cache_dir)
    assert cache_dir.exists()
    assert cache_dir.is_dir()