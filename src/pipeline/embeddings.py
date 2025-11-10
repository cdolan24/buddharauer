"""Embeddings generation module using Ollama's nomic-embed-text model."""
from typing import List
import httpx
import asyncio
from pathlib import Path
import json
import hashlib


class EmbeddingGenerator:
    """Generate embeddings using Ollama's nomic-embed-text model."""

    def __init__(self, cache_dir: str | Path = "data/cache/embeddings"):
        """Initialize the embedding generator.
        
        Args:
            cache_dir: Directory to store embedding cache files
        """
        self.base_url = "http://localhost:11434/api/embeddings"
        self.model = "nomic-embed-text"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_path(self, text: str) -> Path:
        """Get cache file path for text content.
        
        Args:
            text: Text content to generate cache path for
            
        Returns:
            Path to cache file
        """
        # Use hash of text as filename to avoid filesystem issues
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return self.cache_dir / f"{text_hash}.json"

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floating point values representing the embedding
        """
        # Check cache first
        cache_path = self._get_cache_path(text)
        if cache_path.exists():
            with cache_path.open() as f:
                return json.load(f)["embedding"]
        
        # Generate new embedding
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                json={"model": self.model, "prompt": text}
            )
            response.raise_for_status()
            result = response.json()
            if "embedding" not in result:
                raise ValueError(f"No embedding generated for text: {text}")
            embedding = result["embedding"]
            
            # Cache the result
            cache_path.write_text(json.dumps({
                "text": text,
                "embedding": embedding
            }))
            
            return embedding
    
    async def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in parallel.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        # Process in batches to avoid overloading the API
        batch_size = 100
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await asyncio.gather(*[
                self.generate_embedding(text) for text in batch
            ])
            embeddings.extend(batch_embeddings)
            
        return embeddings