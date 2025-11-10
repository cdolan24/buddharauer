"""Embeddings generation module using Ollama's nomic-embed-text model."""
from typing import List, Dict, Optional, Callable
import httpx
import asyncio
from pathlib import Path
import time
from src.utils.logging import get_logger
from .embeddings_cache import EmbeddingsCache

logger = get_logger(__name__)


class EmbeddingError(Exception):
    """Base class for embedding generation errors."""
    pass


class EmbeddingAPIError(EmbeddingError):
    """Error from the Ollama API."""
    pass


class EmbeddingTimeoutError(EmbeddingError):
    """Timeout during embedding generation."""
    pass


class EmbeddingGenerator:
    """Generate embeddings using Ollama's nomic-embed-text model."""

    def __init__(self, 
                cache_dir: str | Path = "data/cache/embeddings",
                batch_size: int = 50,
                max_retries: int = 3,
                timeout: float = 30.0,
                progress_callback: Optional[Callable[[int, int], None]] = None):
        """Initialize the embedding generator.
        
        Args:
            cache_dir: Directory to store embedding cache files
            batch_size: Number of texts to process in parallel
            max_retries: Maximum number of retries for failed API calls
            timeout: Timeout in seconds for each API call
            progress_callback: Optional callback for tracking progress
        """
        self.base_url = "http://localhost:11434/api/embeddings"
        self.model = "nomic-embed-text"
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.timeout = timeout
        self.progress_callback = progress_callback
        self.cache = EmbeddingsCache(cache_dir)
        
    async def _generate_single(self, 
                           text: str, 
                           retry_count: int = 0) -> List[float]:
        """Generate embedding for a single text with retries.
        
        Args:
            text: Text to generate embedding for
            retry_count: Current retry attempt number
            
        Returns:
            List of floating point values representing the embedding
            
        Raises:
            EmbeddingAPIError: If API call fails after all retries
            EmbeddingTimeoutError: If API call times out
        """
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json={"model": self.model, "prompt": text},
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                
                if "embedding" not in result:
                    raise EmbeddingAPIError(f"No embedding in response: {result}")
                    
                return result["embedding"]
                
        except httpx.TimeoutError:
            if retry_count < self.max_retries:
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self._generate_single(text, retry_count + 1)
            raise EmbeddingTimeoutError(f"Timeout after {self.timeout}s")
            
        except httpx.HTTPError as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(2 ** retry_count)
                return await self._generate_single(text, retry_count + 1)
            raise EmbeddingAPIError(f"API error: {str(e)}")
            
        finally:
            elapsed = time.time() - start_time
            if elapsed > self.timeout / 2:  # Log slow requests
                logger.warning(f"Slow embedding generation ({elapsed:.1f}s): {text[:100]}...")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floating point values representing the embedding
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        # Try cache first
        if cached := await self.cache.get(text):
            return cached
            
        # Generate new embedding
        embedding = await self._generate_single(text)
        await self.cache.put(text, embedding)
        return embedding

    async def batch_generate_embeddings(self, 
                                      texts: List[str], 
                                      ignore_errors: bool = False) -> Dict[str, List[float]]:
        """Generate embeddings for multiple texts in parallel.
        
        Args:
            texts: List of texts to generate embeddings for
            ignore_errors: If True, failed embeddings will be skipped
            
        Returns:
            Dictionary mapping texts to their embeddings
        
        Raises:
            EmbeddingError: If any embedding fails and ignore_errors is False
        """
        if not texts:
            return {}
            
        logger.info(f"Generating embeddings for {len(texts)} texts")
        start_time = time.time()
        results = {}
        errors = []
        
        # Get cached embeddings first
        cached = await self.cache.get_batch(texts)
        results.update(cached)
        
        # Generate embeddings for uncached texts
        uncached = [t for t in texts if t not in cached]
        if not uncached:
            return results
            
        logger.info(f"Found {len(cached)} cached embeddings, generating {len(uncached)} new")
        processed = len(cached)
        
        # Process in batches
        for i in range(0, len(uncached), self.batch_size):
            batch = uncached[i:i + self.batch_size]
            
            # Generate embeddings in parallel
            tasks = [self._generate_single(text) for text in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for text, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    if ignore_errors:
                        errors.append((text, str(result)))
                        continue
                    raise result
                results[text] = result
                
            processed += len(batch)
            if self.progress_callback:
                self.progress_callback(processed, len(texts))
                
        # Cache new embeddings
        await self.cache.put_batch({t: e for t, e in results.items() if t in uncached})
        
        elapsed = time.time() - start_time
        logger.info(
            f"Generated {len(results)} embeddings in {elapsed:.1f}s "
            f"({len(errors)} errors, {len(cached)} from cache)"
        )
        
        if errors:
            logger.warning("Failed to generate some embeddings:")
            for text, error in errors[:5]:
                logger.warning(f"- {text[:100]}...: {error}")
            if len(errors) > 5:
                logger.warning(f"  ...and {len(errors)-5} more errors")
                
        return results