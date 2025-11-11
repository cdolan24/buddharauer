"""
Pydantic request models for API validation.

This module defines all request models used in the API endpoints.
Each model provides:
    - Automatic validation of incoming request data
    - Type safety for request handlers
    - OpenAPI documentation generation
    - Clear error messages for invalid requests

Usage Example:
    >>> from fastapi import FastAPI, HTTPException
    >>> from src.api.models.requests import SearchRequest
    >>>
    >>> @app.post("/api/search")
    >>> async def search(request: SearchRequest):
    ...     # FastAPI automatically validates the request
    ...     # and converts it to a SearchRequest object
    ...     results = vector_store.search(
    ...         query=request.query,
    ...         limit=request.limit,
    ...         filters=request.filters
    ...     )
    ...     return {"results": results}
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any


class SearchRequest(BaseModel):
    """
    Request model for vector search operations.

    Attributes:
        query: The search query text
        limit: Maximum number of results to return (1-100)
        filters: Optional metadata filters for search
        include_metadata: Whether to include full metadata in results

    Example:
        {
            "query": "What is the One Ring?",
            "limit": 10,
            "filters": {"document_id": "fellowship"},
            "include_metadata": true
        }
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Search query text"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filters (e.g., {'document_id': 'doc_001'})"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include full metadata in results"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Who is Aragorn?",
                "limit": 5,
                "filters": {"document_id": "fellowship"},
                "include_metadata": True
            }
        }
    )


class DocumentUploadRequest(BaseModel):
    """
    Request model for document upload metadata.

    Note: The actual file upload is handled via FastAPI's UploadFile.
    This model is for additional metadata that accompanies the upload.

    Attributes:
        title: Optional custom title for the document
        metadata: Optional additional metadata tags
        process_immediately: Whether to start processing immediately

    Example:
        {
            "title": "The Fellowship of the Ring",
            "metadata": {"series": "Lord of the Rings", "book": 1},
            "process_immediately": true
        }
    """
    title: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Custom title for the document"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata tags"
    )
    process_immediately: bool = Field(
        default=True,
        description="Start processing immediately after upload"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "The Two Towers",
                "metadata": {"series": "LOTR", "book": 2},
                "process_immediately": True
            }
        }
    )


class ChatRequest(BaseModel):
    """
    Request model for chat/conversation interactions.

    This model supports multi-turn conversations with the FastAgent orchestrator.
    The orchestrator routes questions to appropriate sub-agents based on intent.

    Attributes:
        message: User's question or message
        conversation_id: Unique identifier for conversation thread
        user_id: Optional user identifier for tracking
        context: Optional context information (document filters, mode)

    Example:
        {
            "message": "Who is Aragorn?",
            "conversation_id": "session_123",
            "user_id": "faraday",
            "context": {
                "documents": ["doc_001"],
                "mode": "explanatory"
            }
        }
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User's message or question"
    )
    conversation_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique conversation/session identifier"
    )
    user_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional user identifier"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context (document filters, conversation mode)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Who is Gandalf and what is his role?",
                "conversation_id": "session_abc123",
                "user_id": "faraday",
                "context": {
                    "documents": ["fellowship", "two_towers"],
                    "mode": "explanatory"
                }
            }
        }
    )
