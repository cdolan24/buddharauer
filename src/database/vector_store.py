"""
Simple vector store implementation using numpy for storing and searching embeddings.

This is a temporary implementation that will be replaced with ChromaDB once dependency issues are resolved.
The implementation provides:
- Vector similarity search using cosine similarity
- Metadata filtering for search results
- File-based persistence using JSON
- Integration with Ollama embeddings API

Note: This is an interim solution until ChromaDB compatibility issues with Python 3.14 are resolved.
The API is designed to match ChromaDB's interface for easy migration later.

Example:
    ```python
    store = VectorStore(persist_directory="data/vector_db")
    
    # Add documents
    ids = await store.add_documents(
        texts=["Document 1", "Document 2"],
        metadata_list=[{"source": "doc1"}, {"source": "doc2"}]
    )
    
    # Search
    results = await store.search(
        query_texts=["search query"],
        n_results=5,
        where={"source": "doc1"}
    )
    ```
"""
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import numpy as np
from dataclasses import dataclass, asdict
import hashlib

from src.pipeline.embeddings import EmbeddingGenerator

@dataclass
class Document:
    """A document with its embedding and metadata."""
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]
    id: str


class VectorStore:
    """A simple vector store implementation using numpy arrays."""
    
    def __init__(self, 
                persist_directory: str | Path = "data/vector_db",
                collection_name: str = "documents"):
        """
        Initialize the vector store.
        
        Args:
            persist_directory: Directory to store vector data
            collection_name: Name of the collection
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.collection_path = self.persist_directory / f"{collection_name}.json"
        self.embedding_generator = EmbeddingGenerator()
        
        # Load existing documents or initialize empty
        self.documents: List[Document] = []
        self._load_documents()
    
    def _load_documents(self):
        """Load documents from disk."""
        if self.collection_path.exists():
            with open(self.collection_path, 'r') as f:
                data = json.load(f)
                self.documents = [
                    Document(**doc) for doc in data
                ]
    
    def _save_documents(self):
        """Save documents to disk."""
        with open(self.collection_path, 'w') as f:
            json.dump(
                [asdict(doc) for doc in self.documents],
                f,
                indent=2
            )
    
    def _cosine_similarity(self, query_embedding: List[float], doc_embedding: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        a = np.array(query_embedding)
        b = np.array(doc_embedding)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    async def add_documents(self, 
                          texts: List[str],
                          metadata_list: List[Dict[str, Any]],
                          ids: Optional[List[str]] = None,
                          batch_size: int = 32) -> List[str]:
        """
        Add multiple documents to the store with batched processing.
        
        Args:
            texts: List of text strings
            metadata_list: List of metadata dictionaries
            ids: Optional list of IDs (generated if not provided)
            batch_size: Number of documents to process at once
            
        Returns:
            List of document IDs
        """
        if not texts or not metadata_list:
            return []
            
        if len(texts) != len(metadata_list):
            raise ValueError("texts and metadata_list must have same length")
            
        if ids and len(ids) != len(texts):
            raise ValueError("if provided, ids must have same length as texts")
            
        doc_ids = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadata = metadata_list[i:i + batch_size]
            batch_ids = ids[i:i + batch_size] if ids else None
            
            # Generate embeddings for batch
            batch_embeddings = await self.embedding_generator.batch_generate(batch_texts)
            
            # Generate IDs if needed
            if not batch_ids:
                batch_ids = [
                    hashlib.sha256(text.encode()).hexdigest()
                    for text in batch_texts
                ]
                
            # Create documents
            new_docs = []
            for text, embedding, metadata, doc_id in zip(
                batch_texts, batch_embeddings, batch_metadata, batch_ids):
                doc = Document(
                    text=text,
                    embedding=embedding,
                    metadata=metadata,
                    id=doc_id
                )
                new_docs.append(doc)
                doc_ids.append(doc_id)
                
            # Update documents list
            self.documents.extend(new_docs)
            
            # Save after each batch
            self._save_documents()
            
        return doc_ids
        """
        Add documents to the vector store.
        
        Args:
            texts: List of text chunks to store
            metadata_list: List of metadata dicts for each chunk
            ids: Optional list of IDs for the chunks
            
        Returns:
            List of document IDs that were added
        """
        if not texts:
            return []
        
        # Generate embeddings
        embeddings = await self.embedding_generator.batch_generate_embeddings(texts)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [
                hashlib.sha256(text.encode()).hexdigest()
                for text in texts
            ]
        
        # Create and store documents
        for text, embedding, metadata, doc_id in zip(texts, embeddings, metadata_list, ids):
            doc = Document(
                text=text,
                embedding=embedding,
                metadata=metadata,
                id=doc_id
            )
            self.documents.append(doc)
        
        # Save to disk
        self._save_documents()
        
        return ids
    
    async def search(self,
                    query_texts: List[str],
                    n_results: int = 5,
                    where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Search for similar documents.
        
        Args:
            query_texts: List of query texts to search for
            n_results: Number of results to return per query
            where: Optional filter on metadata
            
        Returns:
            Dictionary containing search results
        """
        results = {
            "ids": [],
            "documents": [],
            "metadatas": [],
            "distances": []
        }
        
        # Generate query embeddings
        query_embeddings = await self.embedding_generator.batch_generate_embeddings(query_texts)
        
        for query_embedding in query_embeddings:
            # Calculate similarities
            similarities = []
            filtered_docs = []
            
            for doc in self.documents:
                # Apply metadata filter if provided
                if where:
                    matches = all(
                        doc.metadata.get(k) == v
                        for k, v in where.items()
                    )
                    if not matches:
                        continue
                
                similarity = self._cosine_similarity(query_embedding, doc.embedding)
                similarities.append((similarity, doc))
                filtered_docs.append(doc)
            
            # Sort by similarity
            similarities.sort(reverse=True)
            top_n = similarities[:n_results]
            
            # Format results
            results["ids"].append([doc.id for _, doc in top_n])
            results["documents"].append([doc.text for _, doc in top_n])
            results["metadatas"].append([doc.metadata for _, doc in top_n])
            results["distances"].append([1 - sim for sim, _ in top_n])  # Convert to distance
        
        return results
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about the vector store collection."""
        return {
            "total_documents": len(self.documents)
        }
    
    def delete_collection(self):
        """Delete the entire collection."""
        if self.collection_path.exists():
            self.collection_path.unlink()
        self.documents = []
        """Delete the entire collection."""
        if self.collection_path.exists():
            self.collection_path.unlink()
        self.documents = []