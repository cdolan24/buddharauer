"""Tests for the enhanced embeddings module."""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
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
    text = "test text for caching enhanced"

    # Create an async mock for the post method
    mock_response = mock_api_response(embedding=mock_embedding)

    # First call - should hit API
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        result1 = await embedding_generator.generate_embedding(text)
        assert mock_instance.post.call_count == 1

    # Second call - should use cache (no API call)
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_api_response(embedding=[0.4, 0.5, 0.6]))
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        result2 = await embedding_generator.generate_embedding(text)
        assert mock_instance.post.call_count == 0  # Should not call API
        assert result2 == result1  # Should return cached value


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
    # httpx uses TimeoutException, not TimeoutError
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        with pytest.raises(EmbeddingTimeoutError):
            await embedding_generator.generate_embedding("test text for timeout")


@pytest.mark.asyncio
async def test_invalid_api_response(embedding_generator):
    """Test handling of invalid API responses."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = AsyncMock()
        # Return response without 'embedding' key
        mock_instance.post = AsyncMock(return_value=mock_api_response(embedding=None))
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        with pytest.raises(EmbeddingAPIError) as exc:
            await embedding_generator.generate_embedding("test text invalid response")
        assert "No embedding in response" in str(exc.value)


@pytest.mark.asyncio
async def test_batch_error_handling(embedding_generator):
    """Test error handling in batch processing."""
    texts = ["text1 for batch error", "text2 for batch error"]

    # Test with errors that will persist through retries
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = AsyncMock()
        # First text succeeds, second consistently fails
        call_count = [0]

        async def mock_post(*args, **kwargs):
            call_count[0] += 1
            # First call succeeds
            if call_count[0] == 1:
                return mock_api_response(embedding=[0.1])
            # Subsequent calls fail (for retries of text2)
            raise httpx.HTTPError("Persistent Error")

        mock_instance.post = mock_post
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        # Should skip errors when ignore_errors=True
        results = await embedding_generator.batch_generate_embeddings(
            texts, ignore_errors=True)
        # Only the first text should succeed
        assert "text1 for batch error" in results
        assert len(results) >= 1  # At least one result


@pytest.mark.asyncio
async def test_progress_tracking(embedding_generator):
    """Test progress callback functionality."""
    progress_calls = []
    embedding_generator.progress_callback = lambda c, t: progress_calls.append((c, t))

    texts = ["text1 progress", "text2 progress", "text3 progress"]
    mock_embedding = [0.1, 0.2, 0.3]

    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_api_response(embedding=mock_embedding))
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        await embedding_generator.batch_generate_embeddings(texts)

    # Should have progress updates for each batch
    assert len(progress_calls) > 0
    assert progress_calls[-1] == (3, 3)  # Final call should be (total, total)