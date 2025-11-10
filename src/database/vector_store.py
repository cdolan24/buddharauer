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
from typing import List, Dict, Optional, Any, TypeVar, Union

from src.pipeline.embeddings import EmbeddingGenerator
from src.pipeline.recovery import with_retry
from src.utils.logging import get_logger

logger = get_logger(__name__)

Vector = Union[List[float], np.ndarray]

def cosine_similarity(a: Vector, b: Vector) -> float:
    """Calculate cosine similarity between two vectors."""
    if isinstance(a, list):
        a = np.array(a)
    if isinstance(b, list):
        b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

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
        
        async def process_batch(batch_start: int) -> List[Document]:
            """Process a batch of documents."""
            batch_end = min(batch_start + batch_size, len(texts))
            batch_texts = texts[batch_start:batch_end]
            batch_metadata = metadata_list[batch_start:batch_end]
            
            # Get batch IDs
            if ids:
                batch_ids = ids[batch_start:batch_end]
            else:
                batch_ids = [
                    hashlib.sha256(text.encode()).hexdigest()
                    for text in batch_texts
                ]
            
            # Generate embeddings
            batch_embeddings_dict = await self.embedding_generator.batch_generate_embeddings(batch_texts)
            batch_embeddings = [batch_embeddings_dict[text] for text in batch_texts]
            
            # Create documents
            return [
                Document(
                    text=text,
                    # Convert embeddings from list to numpy array
                    embedding=embedding,
                    metadata=metadata,
                    id=doc_id
                )
                for text, embedding, metadata, doc_id 
                in zip(batch_texts, batch_embeddings, batch_metadata, batch_ids)
            ]
            
        # Process all batches
        for i in range(0, len(texts), batch_size):
            batch_docs = await process_batch(i)
            doc_ids.extend(doc.id for doc in batch_docs)
            self.documents.extend(batch_docs)
            # Save after each batch
            self._save_documents()
            
        return doc_ids
    
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
        if not query_texts:
            return {
                "ids": [],
                "documents": [],
                "metadatas": [],
                "distances": []
            }

        results = {
            "ids": [[] for _ in query_texts],  # One empty list per query
            "documents": [[] for _ in query_texts],
            "metadatas": [[] for _ in query_texts],
            "distances": [[] for _ in query_texts]
        }

        # Generate query embeddings
        query_embeddings_dict = await self.embedding_generator.batch_generate_embeddings(query_texts)
        logger.info(f"Generated query embeddings: {query_embeddings_dict}")
        query_embeddings = [query_embeddings_dict[text] for text in query_texts]
        logger.info(f"Query embeddings list: {query_embeddings}")
        
        # Filter documents by metadata first if needed
        docs_to_search = self.documents
        if where:
            logger.info(f"Filtering by metadata: {where}")
            for doc in self.documents:
                logger.info(f"Document metadata: {doc.metadata}")
            docs_to_search = [
                doc for doc in self.documents
                if all(doc.metadata.get(k) == v for k, v in where.items())
            ]
            logger.info(f"Found {len(docs_to_search)} matching documents")
            
        # Convert all document embeddings to numpy arrays at once
        if not docs_to_search:
            # Still need one empty list per query
            return {
                "ids": [[] for _ in query_texts],
                "documents": [[] for _ in query_texts], 
                "metadatas": [[] for _ in query_texts],
                "distances": [[] for _ in query_texts]
            }

        # Convert document embeddings to numpy arrays
        logger.info(f"Converting embeddings for {len(docs_to_search)} documents")
        doc_embeddings_list = [doc.embedding for doc in docs_to_search]
        logger.info(f"Document embeddings list: {doc_embeddings_list}")
        doc_embeddings = np.array(doc_embeddings_list, dtype=np.float32)
        
        for query_embedding in query_embeddings:
            # Calculate similarities efficiently using numpy
            query_array = np.array(query_embedding, dtype=np.float32)
            dot_products = np.dot(doc_embeddings, query_array)
            norms = np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(query_array)
            similarities = np.divide(dot_products, norms, out=np.zeros_like(dot_products), where=norms!=0)
            logger.info(f"Similarities: {similarities}")
            
            # Get top N indices (or all if fewer than N)
            k = min(n_results, len(similarities))
            top_indices = np.argsort(similarities)[-k:][::-1]
            logger.info(f"Top indices: {top_indices}")
            
            top_n = [(similarities[i], docs_to_search[i]) for i in top_indices]
            logger.info(f"Top N results: {[(sim, doc.text) for sim, doc in top_n]}")
            
            # Format results
            curr_ids = [doc.id for _, doc in top_n]
            curr_docs = [doc.text for _, doc in top_n]
            curr_metadata = [doc.metadata for _, doc in top_n]
            curr_distances = [1 - sim for sim, _ in top_n]
            
            # Add results
            results["ids"][0] = curr_ids
            results["documents"][0] = curr_docs
            results["metadatas"][0] = curr_metadata  
            results["distances"][0] = curr_distances
        
        return results
    
    def delete_collection(self):
        """Delete the entire collection."""
        if self.collection_path.exists():
            self.collection_path.unlink()
        self.documents = []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        return {
            "total_documents": len(self.documents),
            "embedding_dim": len(self.documents[0].embedding) if self.documents else 0,
            "persist_directory": str(self.persist_directory),
            "collection_path": str(self.collection_path)
        }
            
    @with_retry(max_retries=3, initial_delay=1.0)
    async def add_documents_with_retry(
        self,
        texts: List[str],
        metadata_list: List[Dict[str, Any]],
        batch_size: int = 32
    ) -> List[str]:
        """
        Add documents with retry logic.
        
        Args:
            texts: List of text chunks
            metadata_list: List of metadata dictionaries
            batch_size: Number of documents to process at once
            
        Returns:
            List of document IDs
            
        Raises:
            ValueError: If texts or metadata_list are empty or mismatched
            Exception: For other unexpected errors during document addition
        """
        if not texts or not metadata_list:
            raise ValueError("Texts and metadata lists cannot be empty")
            
        if len(texts) != len(metadata_list):
            raise ValueError("Number of texts must match number of metadata entries")
        
        try:
            return await self.add_documents(
                texts=texts,
                metadata_list=metadata_list,
                batch_size=batch_size
            )
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise