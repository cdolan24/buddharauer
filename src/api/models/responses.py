"""
Pydantic response models for API serialization.

This module defines all response models returned by API endpoints.
Each model provides:
    - Consistent response structure
    - Automatic serialization to JSON
    - Type safety for response data
    - OpenAPI documentation generation

Usage Example:
    >>> from fastapi import FastAPI
    >>> from src.api.models.responses import HealthResponse
    >>>
    >>> @app.get("/api/health", response_model=HealthResponse)
    >>> async def health():
    ...     return HealthResponse(
    ...         status="healthy",
    ...         ollama_connected=True,
    ...         vector_db_status="operational",
    ...         documents_indexed=42
    ...     )
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime


class HealthResponse(BaseModel):
    """
    Response model for system health checks.

    Attributes:
        status: Overall system status (healthy, degraded, unhealthy)
        ollama_connected: Whether Ollama service is reachable
        vector_db_status: Vector database status
        documents_indexed: Number of documents in vector store
        uptime_seconds: API uptime in seconds

    Example:
        {
            "status": "healthy",
            "ollama_connected": true,
            "vector_db_status": "operational",
            "documents_indexed": 47,
            "uptime_seconds": 3600.5
        }
    """
    status: str = Field(
        ...,
        description="Overall system status"
    )
    ollama_connected: bool = Field(
        ...,
        description="Ollama service connectivity"
    )
    vector_db_status: str = Field(
        ...,
        description="Vector database operational status"
    )
    documents_indexed: int = Field(
        ...,
        ge=0,
        description="Number of indexed documents"
    )
    uptime_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="API uptime in seconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "ollama_connected": True,
                "vector_db_status": "operational",
                "documents_indexed": 47,
                "uptime_seconds": 3600.5
            }
        }
    )


class DocumentResponse(BaseModel):
    """
    Response model for a single document.

    Attributes:
        id: Unique document identifier
        title: Document title
        filename: Original filename
        pages: Number of pages
        chunks: Number of chunks
        status: Processing status
        created_at: Upload timestamp
        processed_at: Processing completion timestamp
        metadata: Additional document metadata

    Example:
        {
            "id": "doc_001",
            "title": "Fellowship of the Ring",
            "filename": "fellowship.pdf",
            "pages": 432,
            "chunks": 284,
            "status": "processed",
            "created_at": "2025-01-15T14:23:01Z",
            "processed_at": "2025-01-15T14:25:42Z",
            "metadata": {"series": "LOTR", "book": 1}
        }
    """
    id: str = Field(..., description="Unique document ID")
    title: str = Field(..., description="Document title")
    filename: str = Field(..., description="Original filename")
    pages: int = Field(..., ge=0, description="Number of pages")
    chunks: int = Field(..., ge=0, description="Number of chunks")
    status: str = Field(..., description="Processing status")
    created_at: datetime = Field(..., description="Upload timestamp")
    processed_at: Optional[datetime] = Field(
        default=None,
        description="Processing completion timestamp"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "doc_001",
                "title": "The Fellowship of the Ring",
                "filename": "fellowship.pdf",
                "pages": 432,
                "chunks": 284,
                "status": "processed",
                "created_at": "2025-01-15T14:23:01Z",
                "processed_at": "2025-01-15T14:25:42Z",
                "metadata": {"series": "LOTR", "book": 1}
            }
        }
    )


class DocumentListResponse(BaseModel):
    """
    Response model for document listing.

    Attributes:
        documents: List of document summaries
        total: Total number of documents
        page: Current page number
        page_size: Items per page

    Example:
        {
            "documents": [...],
            "total": 47,
            "page": 1,
            "page_size": 20
        }
    """
    documents: List[DocumentResponse] = Field(
        ...,
        description="List of documents"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of documents"
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Current page number"
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page"
    )


class SearchResult(BaseModel):
    """
    A single search result.

    Attributes:
        chunk_id: Unique chunk identifier
        text: The text content
        score: Relevance score (0-1)
        document_id: Source document ID
        document_title: Source document title
        page: Page number in source document
        metadata: Additional chunk metadata

    Example:
        {
            "chunk_id": "doc_001_chunk_042",
            "text": "Aragorn stepped forward...",
            "score": 0.95,
            "document_id": "doc_001",
            "document_title": "Fellowship of the Ring",
            "page": 42,
            "metadata": {"chapter": "Book 1, Chapter 3"}
        }
    """
    chunk_id: str = Field(..., description="Chunk ID")
    text: str = Field(..., description="Text content")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    document_id: str = Field(..., description="Source document ID")
    document_title: Optional[str] = Field(
        default=None,
        description="Source document title"
    )
    page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Page number"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata"
    )


class SearchResponse(BaseModel):
    """
    Response model for search operations.

    Attributes:
        results: List of search results
        query: Original search query
        total_results: Total number of results found
        processing_time_ms: Search processing time in milliseconds

    Example:
        {
            "results": [...],
            "query": "Who is Aragorn?",
            "total_results": 5,
            "processing_time_ms": 23.4
        }
    """
    results: List[SearchResult] = Field(
        ...,
        description="Search results"
    )
    query: str = Field(..., description="Original query")
    total_results: int = Field(
        ...,
        ge=0,
        description="Total results found"
    )
    processing_time_ms: float = Field(
        ...,
        ge=0.0,
        description="Processing time in milliseconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "results": [
                    {
                        "chunk_id": "doc_001_chunk_042",
                        "text": "Aragorn stepped forward...",
                        "score": 0.95,
                        "document_id": "doc_001",
                        "document_title": "Fellowship of the Ring",
                        "page": 42,
                        "metadata": {"chapter": "Book 1, Chapter 3"}
                    }
                ],
                "query": "Who is Aragorn?",
                "total_results": 1,
                "processing_time_ms": 23.4
            }
        }
    )


class ErrorResponse(BaseModel):
    """
    Response model for error responses.

    Attributes:
        error: Error type/code
        message: Human-readable error message
        details: Optional additional error details

    Example:
        {
            "error": "ValidationError",
            "message": "Query text must be between 1 and 5000 characters",
            "details": {"field": "query", "value_length": 5001}
        }
    """
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "NotFoundError",
                "message": "Document not found",
                "details": {"document_id": "doc_999"}
            }
        }
    )


class SourceReference(BaseModel):
    """
    A source reference for chat responses.

    Represents a document chunk that was used to generate the response.
    Includes metadata for citation and navigation.

    Attributes:
        document_id: Source document identifier
        document_title: Human-readable document title
        chunk_id: Specific chunk identifier
        page: Page number in source document
        text: Excerpt from the source
        relevance_score: How relevant this source is (0-1)

    Example:
        {
            "document_id": "doc_001",
            "document_title": "Fellowship of the Ring",
            "chunk_id": "doc_001_chunk_042",
            "page": 42,
            "text": "Aragorn stepped forward...",
            "relevance_score": 0.95
        }
    """
    document_id: str = Field(..., description="Source document ID")
    document_title: str = Field(..., description="Document title")
    chunk_id: str = Field(..., description="Chunk ID")
    page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Page number"
    )
    text: str = Field(..., description="Source text excerpt")
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score"
    )


class ChatResponse(BaseModel):
    """
    Response model for chat/conversation interactions.

    Contains the agent's response along with source citations and metadata.
    The response may come from different agents (orchestrator, analyst, retrieval).

    Attributes:
        response: The agent's response text
        sources: List of source document references
        conversation_id: Conversation identifier
        agent_used: Which agent generated the response
        processing_time_ms: Response generation time in milliseconds
        metadata: Additional response metadata

    Example:
        {
            "response": "Aragorn is a ranger and the heir to the throne...",
            "sources": [
                {
                    "document_id": "doc_001",
                    "document_title": "Fellowship of the Ring",
                    "chunk_id": "doc_001_chunk_042",
                    "page": 42,
                    "text": "Aragorn stepped forward...",
                    "relevance_score": 0.95
                }
            ],
            "conversation_id": "session_123",
            "agent_used": "orchestrator",
            "processing_time_ms": 1234.5,
            "metadata": {"query_type": "question"}
        }
    """
    response: str = Field(..., description="Agent's response text")
    sources: List[SourceReference] = Field(
        default_factory=list,
        description="Source document references"
    )
    conversation_id: str = Field(..., description="Conversation ID")
    agent_used: str = Field(..., description="Agent that handled the query")
    processing_time_ms: float = Field(
        ...,
        ge=0.0,
        description="Processing time in milliseconds"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "response": "Aragorn is a ranger and the rightful heir to the throne of Gondor...",
                "sources": [
                    {
                        "document_id": "doc_001",
                        "document_title": "The Fellowship of the Ring",
                        "chunk_id": "doc_001_chunk_042",
                        "page": 42,
                        "text": "Aragorn, son of Arathorn, stepped forward...",
                        "relevance_score": 0.95
                    }
                ],
                "conversation_id": "session_abc123",
                "agent_used": "orchestrator",
                "processing_time_ms": 1234.5,
                "metadata": {"query_type": "question", "mode": "explanatory"}
            }
        }
    )
