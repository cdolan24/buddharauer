"""Tests for embedding generation."""
import pytest
from pathlib import Path
import json
import hashlib
from src.pipeline.embeddings import EmbeddingGenerator


@pytest.fixture
def embedding_generator():
    """Create a test embedding generator."""
    # Use a temporary test cache directory
    return EmbeddingGenerator(cache_dir="tests/data/test_cache/embeddings")


@pytest.mark.asyncio
async def test_embedding_generation(embedding_generator):
    """Test generating an embedding for a single text."""
    text = "Test text for embedding"
    embedding = await embedding_generator.generate_embedding(text)
    
    # Basic validation
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.asyncio
async def test_embedding_caching(embedding_generator):
    """Test that embeddings are properly cached."""
    text = "Test text for caching"
    
    # Generate first time (should hit Ollama API)
    embedding1 = await embedding_generator.generate_embedding(text)
    
    # Get cache path and verify file exists
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    cache_path = embedding_generator.cache_dir / f"{text_hash}.json"
    assert cache_path.exists()
    
    # Read cached data
    with cache_path.open() as f:
        cached_data = json.load(f)
    assert cached_data["text"] == text
    assert cached_data["embedding"] == embedding1
    
    # Generate second time (should hit cache)
    embedding2 = await embedding_generator.generate_embedding(text)
    assert embedding2 == embedding1


@pytest.mark.asyncio
async def test_batch_embedding_generation(embedding_generator):
    """Test generating embeddings for multiple texts."""
    texts = [
        "First test text",
        "Second test text",
        "Third test text"
    ]
    
    embeddings = await embedding_generator.batch_generate_embeddings(texts)
    
    assert len(embeddings) == len(texts)
    assert all(isinstance(emb, list) for emb in embeddings)
    assert all(isinstance(x, float) for emb in embeddings for x in emb)


def test_cache_directory_creation(tmp_path):
    """Test that the cache directory is created if it doesn't exist."""
    cache_dir = tmp_path / "new_cache"
    EmbeddingGenerator(cache_dir=cache_dir)
    assert cache_dir.exists()
    assert cache_dir.is_dir()