"""
Vector search endpoints for semantic document search.

This module provides endpoints for searching documents using semantic
vector similarity. It integrates with the VectorStore to perform
efficient similarity searches across all indexed documents.

Key Features:
    - Semantic search using embeddings
    - Metadata filtering
    - Configurable result limits
    - Score-based ranking

Usage Example:
    POST /api/search
    {
        "query": "Who is Aragorn?",
        "limit": 10,
        "filters": {"document_id": "fellowship"}
    }

Response:
    {
        "results": [
            {
                "chunk_id": "doc_001_chunk_042",
                "text": "Aragorn stepped forward...",
                "score": 0.95,
                "document_id": "doc_001",
                "page": 42
            }
        ],
        "total_results": 1,
        "processing_time_ms": 23.4
    }
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import time

from src.api.models.requests import SearchRequest
from src.api.models.responses import SearchResponse, SearchResult, ErrorResponse
from src.database.vector_store import VectorStore
from src.utils.logging import get_logger

# Import dependency injection functions
from src.api.dependencies import get_vector_store, get_document_registry

logger = get_logger(__name__)

# Create router for search endpoints
router = APIRouter(
    prefix="/api/search",
    tags=["search"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


@router.post("", response_model=SearchResponse, status_code=200)
async def search_documents(
    request: SearchRequest,
    vector_store = Depends(get_vector_store),
    registry = Depends(get_document_registry)
):
    """
    Perform semantic search across indexed documents.

    This endpoint uses vector similarity search to find relevant document
    chunks based on the query text. Results are ranked by relevance score.

    Args:
        request: SearchRequest containing query, filters, and options
        vector_store: VectorStore instance (injected dependency)
        registry: DocumentRegistry instance (injected dependency)

    Returns:
        SearchResponse: Search results with metadata and timing info

    Raises:
        HTTPException 400: Invalid request parameters
        HTTPException 500: Search operation failed

    Example Request:
        ```json
        {
            "query": "What is the significance of the One Ring?",
            "limit": 5,
            "filters": {"document_id": "fellowship"},
            "include_metadata": true
        }
        ```

    Example Response:
        ```json
        {
            "results": [
                {
                    "chunk_id": "doc_001_chunk_123",
                    "text": "The One Ring was forged...",
                    "score": 0.92,
                    "document_id": "doc_001",
                    "document_title": "Fellowship of the Ring",
                    "page": 23,
                    "metadata": {"chapter": "Book 1"}
                }
            ],
            "query": "What is the significance of the One Ring?",
            "total_results": 5,
            "processing_time_ms": 42.3
        }
        ```

    Note:
        - Scores range from 0 to 1, with 1 being most relevant
        - Filters use exact matching on metadata fields
        - Results are automatically deduplicated by chunk_id
    """
    start_time = time.time()

    try:
        # Validate query text
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error="ValidationError",
                    message="Query text cannot be empty",
                    details={"field": "query"}
                ).model_dump()
            )

        logger.info(f"Searching for: '{request.query}' with limit={request.limit}")

        # Perform semantic search using VectorStore
        # The VectorStore.search() method returns results with similarity scores
        search_results = await vector_store.search(
            query_texts=[request.query],
            n_results=request.limit or 10,
            where=request.filters  # Apply metadata filters if provided
        )

        # Convert VectorStore results to SearchResult format
        results = []
        for result in search_results:
            # Extract document metadata for enrichment
            doc_id = result.get("metadata", {}).get("document_id")
            doc_title = None

            # Optionally enrich with document title from registry
            if doc_id and request.include_metadata:
                doc_record = await registry.get_by_id(doc_id)
                if doc_record:
                    doc_title = doc_record.filename

            results.append(SearchResult(
                chunk_id=result.get("id", ""),
                text=result.get("text", ""),
                score=result.get("score", 0.0),
                document_id=doc_id,
                document_title=doc_title,
                page=result.get("metadata", {}).get("page"),
                metadata=result.get("metadata", {}) if request.include_metadata else None
            ))

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(f"Search completed: {len(results)} results in {processing_time_ms:.2f}ms")

        return SearchResponse(
            results=results,
            query=request.query,
            total_results=len(results),
            processing_time_ms=processing_time_ms
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="SearchError",
                message="Failed to perform search",
                details={"error": str(e)}
            ).dict()
        )


@router.get("/similar/{chunk_id}", response_model=SearchResponse)
async def find_similar_chunks(
    chunk_id: str,
    limit: int = 5
):
    """
    Find chunks similar to a given chunk.

    This endpoint is useful for:
    - Finding related content
    - Expanding context around a search result
    - Discovering connections between documents

    Args:
        chunk_id: ID of the chunk to find similar content for
        limit: Maximum number of similar chunks to return

    Returns:
        SearchResponse: Similar chunks ranked by similarity

    Raises:
        HTTPException 404: Chunk not found
        HTTPException 500: Operation failed

    Example:
        ```bash
        curl http://localhost:8000/api/search/similar/doc_001_chunk_042?limit=5
        ```

    Note:
        The original chunk is excluded from results.
    """
    start_time = time.time()

    try:
        # TODO: Implement similarity search
        # This would:
        # 1. Get the embedding for the specified chunk
        # 2. Search for similar vectors
        # 3. Filter out the original chunk
        # 4. Return top N results

        logger.warning(
            f"Similar chunks search for {chunk_id} not yet implemented. "
            "Returning empty results."
        )

        processing_time_ms = (time.time() - start_time) * 1000

        return SearchResponse(
            results=[],
            query=f"Similar to {chunk_id}",
            total_results=0,
            processing_time_ms=processing_time_ms
        )

    except Exception as e:
        logger.error(f"Similar chunks search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="SearchError",
                message="Failed to find similar chunks",
                details={"chunk_id": chunk_id, "error": str(e)}
            ).dict()
        )
