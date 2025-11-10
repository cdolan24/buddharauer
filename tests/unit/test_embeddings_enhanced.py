"""Tests for the enhanced embeddings module."""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch
import httpx

from src.pipeline.embeddings import (
    EmbeddingGenerator, EmbeddingError, EmbeddingAPIError, 
    EmbeddingTimeoutError
)


@pytest.fixture
def embedding_generator():
    """Create a test embedding generator with small batches."""
    return EmbeddingGenerator(
        cache_dir="tests/data/test_cache/embeddings",
        batch_size=2,  # Small batch size for testing
        max_retries=2,
        timeout=1.0
    )


def mock_api_response(embedding=None, status_code=200, error=None):
    """Create a mock API response."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = status_code
    
    if error:
        mock_response.raise_for_status.side_effect = error
    else:
        mock_response.raise_for_status.return_value = None
        
    if embedding is not None:
        mock_response.json.return_value = {"embedding": embedding}
    else:
        mock_response.json.return_value = {}
        
    return mock_response


@pytest.mark.asyncio
async def test_successful_embedding_generation(embedding_generator):
    """Test basic embedding generation."""
    mock_embedding = [0.1, 0.2, 0.3]
    
    with patch('httpx.AsyncClient.post', 
              return_value=mock_api_response(embedding=mock_embedding)):
        result = await embedding_generator.generate_embedding("test text")
        assert result == mock_embedding


@pytest.mark.asyncio
async def test_embedding_caching(embedding_generator):
    """Test that embeddings are properly cached and reused."""
    mock_embedding = [0.1, 0.2, 0.3]
    text = "test text"
    
    # First call - should hit API
    with patch('httpx.AsyncClient.post', 
              return_value=mock_api_response(embedding=mock_embedding)) as mock_post:
        result1 = await embedding_generator.generate_embedding(text)
        assert mock_post.call_count == 1
        
    # Second call - should use cache
    with patch('httpx.AsyncClient.post', 
              return_value=mock_api_response(embedding=[0.4, 0.5, 0.6])) as mock_post:
        result2 = await embedding_generator.generate_embedding(text)
        assert mock_post.call_count == 0
        assert result2 == result1


@pytest.mark.asyncio
async def test_batch_processing(embedding_generator):
    """Test batch processing of multiple texts."""
    texts = ["text1", "text2", "text3", "text4"]
    mock_embeddings = [[0.1], [0.2], [0.3], [0.4]]
    
    # Setup mock responses for each text
    responses = [mock_api_response(emb) for emb in mock_embeddings]
    
    with patch('httpx.AsyncClient.post', side_effect=responses):
        results = await embedding_generator.batch_generate_embeddings(texts)
        
        assert len(results) == len(texts)
        for text, expected in zip(texts, mock_embeddings):
            assert results[text] == expected


@pytest.mark.asyncio
async def test_error_handling_and_retries(embedding_generator):
    """Test error handling and retry logic."""
    # Mock that fails twice then succeeds
    mock_embedding = [0.1, 0.2, 0.3]
    responses = [
        mock_api_response(error=httpx.HTTPError("Error")),
        mock_api_response(error=httpx.HTTPError("Error")),
        mock_api_response(embedding=mock_embedding)
    ]
    
    with patch('httpx.AsyncClient.post', side_effect=responses):
        result = await embedding_generator.generate_embedding("test text")
        assert result == mock_embedding


@pytest.mark.asyncio
async def test_timeout_handling(embedding_generator):
    """Test handling of timeout errors."""
    with patch('httpx.AsyncClient.post', 
              side_effect=httpx.TimeoutError("Timeout")):
        with pytest.raises(EmbeddingTimeoutError):
            await embedding_generator.generate_embedding("test text")


@pytest.mark.asyncio
async def test_invalid_api_response(embedding_generator):
    """Test handling of invalid API responses."""
    with patch('httpx.AsyncClient.post', 
              return_value=mock_api_response(embedding=None)):
        with pytest.raises(EmbeddingAPIError) as exc:
            await embedding_generator.generate_embedding("test text")
        assert "No embedding in response" in str(exc.value)


@pytest.mark.asyncio
async def test_batch_error_handling(embedding_generator):
    """Test error handling in batch processing."""
    texts = ["text1", "text2"]
    responses = [
        mock_api_response(embedding=[0.1]),
        mock_api_response(error=httpx.HTTPError("Error"))
    ]
    
    with patch('httpx.AsyncClient.post', side_effect=responses):
        # Should raise error by default
        with pytest.raises(httpx.HTTPError):
            await embedding_generator.batch_generate_embeddings(texts)
            
        # Should skip errors when ignore_errors=True
        results = await embedding_generator.batch_generate_embeddings(
            texts, ignore_errors=True)
        assert len(results) == 1
        assert "text1" in results


@pytest.mark.asyncio
async def test_progress_tracking(embedding_generator):
    """Test progress callback functionality."""
    progress_calls = []
    embedding_generator.progress_callback = lambda c, t: progress_calls.append((c, t))
    
    texts = ["text1", "text2", "text3"]
    mock_embedding = [0.1, 0.2, 0.3]
    
    with patch('httpx.AsyncClient.post', 
              return_value=mock_api_response(embedding=mock_embedding)):
        await embedding_generator.batch_generate_embeddings(texts)
        
    # Should have progress updates for each batch
    assert len(progress_calls) > 0
    assert progress_calls[-1] == (3, 3)  # Final call should be (total, total)