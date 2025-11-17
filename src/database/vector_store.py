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
    """
    Calculate cosine similarity between two vectors.

    Computes the cosine similarity metric, which measures the cosine of the angle
    between two vectors. Returns a value between -1 and 1, where 1 means the
    vectors are identical in direction, 0 means orthogonal, and -1 means opposite.

    Args:
        a: First vector, either as list of floats or numpy array
        b: Second vector, either as list of floats or numpy array

    Returns:
        float: Cosine similarity score between -1.0 and 1.0

    Example:
        >>> vec1 = [1.0, 2.0, 3.0]
        >>> vec2 = [2.0, 4.0, 6.0]
        >>> similarity = cosine_similarity(vec1, vec2)
        >>> print(f"Similarity: {similarity:.3f}")  # 1.000 (identical direction)
    """
    # Convert lists to numpy arrays for efficient computation
    if isinstance(a, list):
        a = np.array(a)
    if isinstance(b, list):
        b = np.array(b)

    # Compute cosine similarity: dot(a,b) / (||a|| * ||b||)
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

    def _validate_add_documents_input(
        self,
        texts: List[str],
        metadata_list: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Validate inputs for add_documents methods.

        Args:
            texts: List of text strings to validate
            metadata_list: List of metadata dictionaries to validate
            ids: Optional list of IDs to validate

        Raises:
            ValueError: If inputs are invalid or mismatched
        """
        if not texts or not metadata_list:
            raise ValueError("Texts and metadata lists cannot be empty")

        if len(texts) != len(metadata_list):
            raise ValueError("Number of texts must match number of metadata entries")

        if ids and len(ids) != len(texts):
            raise ValueError("If provided, ids must have same length as texts")

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
        # Validate inputs using centralized validation
        self._validate_add_documents_input(texts, metadata_list, ids)
            
        doc_ids = []
        
        async def process_batch(batch_start: int) -> List[Document]:
            """
            Process a single batch of documents with embeddings.

            Handles text slicing, ID generation, embedding computation,
            and Document object creation for a subset of inputs.

            Args:
                batch_start: Starting index for this batch

            Returns:
                List of Document objects with computed embeddings
            """
            # Calculate batch boundaries (handle edge case of last batch)
            batch_end = min(batch_start + batch_size, len(texts))
            batch_texts = texts[batch_start:batch_end]
            batch_metadata = metadata_list[batch_start:batch_end]

            # Generate or use provided IDs for this batch
            if ids:
                # Use pre-provided IDs if available
                batch_ids = ids[batch_start:batch_end]
            else:
                # Generate deterministic IDs from content hash
                batch_ids = [
                    hashlib.sha256(text.encode()).hexdigest()
                    for text in batch_texts
                ]

            # Generate embeddings for all texts in batch (concurrent API call)
            batch_embeddings_dict = await self.embedding_generator.batch_generate_embeddings(batch_texts)
            # Preserve order by mapping back to original text order
            batch_embeddings = [batch_embeddings_dict[text] for text in batch_texts]

            # Create Document objects combining text, embeddings, metadata, and IDs
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
            # Calculate cosine similarities efficiently using vectorized numpy operations
            # Formula: cosine_sim = dot(query, doc) / (||query|| * ||doc||)

            # Convert query embedding to numpy array for efficient computation
            query_array = np.array(query_embedding, dtype=np.float32)

            # Compute dot products between query and all documents (vectorized)
            dot_products = np.dot(doc_embeddings, query_array)

            # Compute L2 norms: ||query|| * ||doc|| for all documents
            norms = np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(query_array)

            # Compute cosine similarities with safe division (avoid divide-by-zero)
            # Returns 0 for zero-norm vectors instead of NaN
            similarities = np.divide(dot_products, norms, out=np.zeros_like(dot_products), where=norms!=0)
            logger.info(f"Similarities: {similarities}")

            # Select top N most similar documents
            # Get k (min of requested n_results and available documents)
            k = min(n_results, len(similarities))
            # argsort returns indices sorted ascending, so take last k and reverse
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
    
    def get_by_id(self, doc_id: str) -> Optional[Document]:
        """
        Retrieve a document by its ID.

        Useful for getting specific document chunks, especially when retrieving
        context around a specific chunk (e.g., getting surrounding chunks).

        Args:
            doc_id: Unique identifier of the document to retrieve

        Returns:
            Document object if found, None otherwise

        Example:
            >>> store = VectorStore(persist_directory="./db")
            >>> doc = store.get_by_id("doc_001_chunk_042")
            >>> if doc:
            ...     print(f"Found: {doc.text[:50]}...")
        """
        # Search through documents for matching ID
        # Note: Linear search is acceptable for MVP; ChromaDB will optimize this
        for doc in self.documents:
            if doc.id == doc_id:
                return doc

        # Document not found
        return None

    def get_by_ids(self, doc_ids: List[str]) -> List[Optional[Document]]:
        """
        Retrieve multiple documents by their IDs.

        More efficient than calling get_by_id() multiple times when retrieving
        many documents. Maintains order of input IDs in results.

        Args:
            doc_ids: List of document IDs to retrieve

        Returns:
            List of Document objects (or None for IDs not found)
            Order matches input doc_ids

        Example:
            >>> store = VectorStore(persist_directory="./db")
            >>> ids = ["doc_001_chunk_040", "doc_001_chunk_041", "doc_001_chunk_042"]
            >>> docs = store.get_by_ids(ids)
            >>> for doc_id, doc in zip(ids, docs):
            ...     if doc:
            ...         print(f"{doc_id}: {doc.text[:30]}...")
        """
        # Create ID lookup dictionary for O(1) access per document
        # This is more efficient than nested loops for multiple IDs
        id_to_doc = {doc.id: doc for doc in self.documents}

        # Return documents in same order as requested IDs
        # Use .get() to return None for missing IDs instead of raising KeyError
        return [id_to_doc.get(doc_id) for doc_id in doc_ids]

    def delete_collection(self):
        """
        Delete the entire collection and all its documents.

        WARNING: This operation is irreversible. All documents and their embeddings
        will be permanently removed from both memory and disk storage.

        Side Effects:
            - Deletes the collection file from disk (if exists)
            - Clears all documents from memory
            - Cannot be undone

        Example:
            >>> store = VectorStore(persist_directory="./db")
            >>> store.delete_collection()  # All data will be lost!
        """
        # Remove persisted collection file if it exists
        if self.collection_path.exists():
            self.collection_path.unlink()

        # Clear in-memory documents
        self.documents = []

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics and metadata about the current collection.

        Returns:
            Dictionary containing collection statistics with keys:
                - total_documents (int): Number of documents in collection
                - embedding_dim (int): Dimensionality of embeddings (0 if empty)
                - persist_directory (str): Path to persistence directory
                - collection_path (str): Path to collection JSON file

        Example:
            >>> store = VectorStore(persist_directory="./db")
            >>> stats = store.get_collection_stats()
            >>> print(f"Collection has {stats['total_documents']} documents")
            >>> print(f"Embedding dimension: {stats['embedding_dim']}")
        """
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
        # Validate inputs using centralized validation
        self._validate_add_documents_input(texts, metadata_list)

        try:
            return await self.add_documents(
                texts=texts,
                metadata_list=metadata_list,
                batch_size=batch_size
            )
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise