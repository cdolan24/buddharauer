"""Cache management for embeddings."""
from typing import List, Dict, Optional, Set
from pathlib import Path
import json
import hashlib
import time
import asyncio
from contextlib import asynccontextmanager
import aiofiles
import aiofiles.os

class EmbeddingsCache:
    """Manages caching of embeddings with optimized async I/O."""
    
    def __init__(self, cache_dir: str | Path):
        """Initialize the embeddings cache.
        
        Args:
            cache_dir: Directory to store embedding cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._write_locks: Dict[str, asyncio.Lock] = {}
        
    def _get_cache_path(self, text: str) -> Path:
        """Get cache file path for text content."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return self.cache_dir / f"{text_hash}.json"
    
    @asynccontextmanager
    async def _get_write_lock(self, cache_path: str):
        """Get a lock for writing to a specific cache file."""
        if cache_path not in self._write_locks:
            self._write_locks[cache_path] = asyncio.Lock()
        try:
            await self._write_locks[cache_path].acquire()
            yield
        finally:
            self._write_locks[cache_path].release()
            
    async def get(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache if it exists.
        
        Args:
            text: Text to get embedding for
            
        Returns:
            Cached embedding or None if not found
        """
        cache_path = self._get_cache_path(text)
        if not cache_path.exists():
            return None
            
        try:
            async with aiofiles.open(cache_path, 'r') as f:
                data = json.loads(await f.read())
                return data["embedding"]
        except (json.JSONDecodeError, KeyError, IOError):
            # If cache is corrupted, delete it
            try:
                await aiofiles.os.remove(cache_path)
            except IOError:
                pass
            return None
            
    async def put(self, text: str, embedding: List[float]):
        """Cache an embedding.
        
        Args:
            text: Original text
            embedding: Generated embedding
        """
        cache_path = self._get_cache_path(text)
        cache_data = {
            "text": text,
            "embedding": embedding,
            "timestamp": time.time()
        }
        
        async with self._get_write_lock(str(cache_path)):
            try:
                async with aiofiles.open(cache_path, 'w') as f:
                    await f.write(json.dumps(cache_data))
            except IOError:
                # Log error but don't fail - caching is optional
                pass
                
    async def get_batch(self, texts: List[str]) -> Dict[str, List[float]]:
        """Get multiple embeddings from cache.
        
        Args:
            texts: List of texts to get embeddings for
            
        Returns:
            Dictionary mapping texts to their cached embeddings
        """
        tasks = [self.get(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        cached = {}
        for text, result in zip(texts, results):
            if isinstance(result, list):  # Valid embedding
                cached[text] = result
        return cached
        
    async def put_batch(self, text_embeddings: Dict[str, List[float]]):
        """Cache multiple embeddings.
        
        Args:
            text_embeddings: Dictionary mapping texts to embeddings
        """
        await asyncio.gather(*[
            self.put(text, embedding) 
            for text, embedding in text_embeddings.items()
        ])
        
    def get_uncached_texts(self, texts: List[str]) -> Set[str]:
        """Get texts that are not in the cache.
        
        Args:
            texts: List of texts to check
            
        Returns:
            Set of texts not found in cache
        """
        uncached = set()
        for text in texts:
            if not self._get_cache_path(text).exists():
                uncached.add(text)
        return uncached