"""
Vector Database MCP Tools for FastAgent.

This module provides MCP tools for interacting with the vector database.
These tools are used by the retrieval agent to search for and retrieve
relevant document chunks.

Key Features:
    - Semantic search across document chunks
    - Context expansion (getting surrounding chunks)
    - Metadata filtering
    - Result re-ranking

Usage:
    >>> from src.agents.tools.vector_db_tools import create_vector_search_tool
    >>> from src.database.vector_store import VectorStore
    >>>
    >>> vector_store = VectorStore()
    >>> search_tool = create_vector_search_tool(vector_store)
    >>> # Register tool with FastAgent agent
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import asdict

# FastAgent imports (conditional)
try:
    from fastagent.core import tool
    FASTAGENT_AVAILABLE = True
except ImportError:
    FASTAGENT_AVAILABLE = False
    # Mock decorator for when FastAgent is not available
    def tool(func):
        return func

from src.database.vector_store import VectorStore

logger = logging.getLogger(__name__)


def create_vector_search_tool(vector_store: VectorStore):
    """
    Create a FastAgent tool for semantic vector search.

    This tool allows agents to search the vector database for relevant
    document chunks based on semantic similarity.

    Args:
        vector_store: VectorStore instance to search

    Returns:
        Tool function decorated with @tool for FastAgent

    Example:
        >>> vector_store = VectorStore()
        >>> search_tool = create_vector_search_tool(vector_store)
        >>> # Agent will use this tool to search documents
    """
    @tool
    async def search_vector_db(
        query: str,
        limit: int = 5,
        min_score: float = 0.0,
        document_id: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search the vector database for relevant document chunks.

        Performs semantic search using embeddings to find the most relevant
        document chunks matching the query.

        Args:
            query: Search query text
            limit: Maximum number of results to return (default: 5)
            min_score: Minimum similarity score threshold (default: 0.0)
            document_id: Optional filter by specific document
            metadata_filter: Optional metadata filters (e.g., {"page": 42})

        Returns:
            Dictionary containing:
                - results: List of matching chunks with metadata
                - count: Number of results returned
                - query: Original query text

        Example:
            >>> results = await search_vector_db("Who is Aragorn?", limit=3)
            >>> for result in results["results"]:
            ...     print(f"{result['text']} (score: {result['score']:.2f})")
        """
        try:
            # Build filters
            filters = {}
            if document_id:
                filters["document_id"] = document_id
            if metadata_filter:
                filters.update(metadata_filter)

            # Execute search
            search_results = vector_store.search(
                query=query,
                limit=limit,
                filters=filters if filters else None
            )

            # Filter by minimum score
            filtered_results = [
                r for r in search_results
                if r.get("score", 0.0) >= min_score
            ]

            # Format results
            formatted_results = []
            for result in filtered_results[:limit]:
                formatted_results.append({
                    "chunk_id": result.get("chunk_id", ""),
                    "document_id": result.get("document_id", ""),
                    "document_title": result.get("document_title", "Unknown"),
                    "text": result.get("text", ""),
                    "page": result.get("page"),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {})
                })

            logger.info(
                f"Vector search completed: {len(formatted_results)} results "
                f"for query '{query[:50]}...'"
            )

            return {
                "results": formatted_results,
                "count": len(formatted_results),
                "query": query
            }

        except Exception as e:
            logger.error(f"Vector search tool error: {e}", exc_info=True)
            return {
                "results": [],
                "count": 0,
                "query": query,
                "error": str(e)
            }

    return search_vector_db


def create_chunk_context_tool(vector_store: VectorStore):
    """
    Create a FastAgent tool for retrieving chunk context.

    This tool retrieves surrounding chunks (before/after) for a given chunk,
    providing additional context for better understanding.

    Args:
        vector_store: VectorStore instance to search

    Returns:
        Tool function decorated with @tool for FastAgent

    Example:
        >>> context_tool = create_chunk_context_tool(vector_store)
        >>> # Agent will use this to get surrounding text
    """
    @tool
    async def get_chunk_context(
        chunk_id: str,
        before: int = 1,
        after: int = 1
    ) -> Dict[str, Any]:
        """
        Get surrounding chunks for context.

        Retrieves the chunks immediately before and after a given chunk
        to provide additional context.

        Args:
            chunk_id: ID of the chunk to get context for
            before: Number of chunks before to retrieve (default: 1)
            after: Number of chunks after to retrieve (default: 1)

        Returns:
            Dictionary containing:
                - chunk: The requested chunk
                - before_chunks: List of chunks before
                - after_chunks: List of chunks after
                - document_id: Document ID
                - total_context: Combined text of all chunks

        Example:
            >>> context = await get_chunk_context("doc_001_chunk_042", before=2, after=2)
            >>> print(context["total_context"])
        """
        try:
            # Parse chunk_id to extract document and chunk number
            # Format: "doc_001_chunk_042"
            parts = chunk_id.split("_chunk_")
            if len(parts) != 2:
                return {
                    "error": "Invalid chunk_id format",
                    "chunk": None,
                    "before_chunks": [],
                    "after_chunks": []
                }

            document_id = parts[0]
            chunk_num = int(parts[1])

            # Get surrounding chunk IDs
            chunk_ids = []
            for i in range(chunk_num - before, chunk_num + after + 1):
                if i >= 0:  # Don't go below 0
                    chunk_ids.append(f"{document_id}_chunk_{i:03d}")

            # Retrieve chunks using VectorStore.get_by_ids()
            # This efficiently fetches all chunks in a single operation
            chunks = vector_store.get_by_ids(chunk_ids)

            # Find the target chunk and split into before/after
            target_idx = before  # Target chunk is at index 'before' in results
            target_chunk = chunks[target_idx] if target_idx < len(chunks) else None

            # Split chunks into before and after groups
            before_chunks = [c for c in chunks[:target_idx] if c is not None]
            after_chunks = [c for c in chunks[target_idx + 1:] if c is not None]

            # Combine all text for total context
            # Useful for passing full context to agent
            total_context = ""
            if before_chunks:
                total_context += "\n\n".join(c.text for c in before_chunks) + "\n\n"
            if target_chunk:
                total_context += target_chunk.text
            if after_chunks:
                total_context += "\n\n" + "\n\n".join(c.text for c in after_chunks)

            logger.info(
                f"Context retrieval for {chunk_id}: "
                f"{len(before_chunks)} before, {len(after_chunks)} after"
            )

            return {
                "chunk_id": chunk_id,
                "chunk": target_chunk.to_dict() if target_chunk and hasattr(target_chunk, 'to_dict') else (asdict(target_chunk) if target_chunk else None),
                "before_chunks": [asdict(c) for c in before_chunks],
                "after_chunks": [asdict(c) for c in after_chunks],
                "document_id": document_id,
                "total_context": total_context.strip()
            }

        except Exception as e:
            logger.error(f"Chunk context tool error: {e}", exc_info=True)
            return {
                "error": str(e),
                "chunk": None,
                "before_chunks": [],
                "after_chunks": []
            }

    return get_chunk_context
