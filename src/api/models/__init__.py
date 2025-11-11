"""
Pydantic models for API request and response validation.

This module defines data models used throughout the API for:
    - Request validation
    - Response serialization
    - Type safety
    - API documentation

All models use Pydantic for automatic validation and OpenAPI schema generation.
"""

from .requests import SearchRequest, DocumentUploadRequest
from .responses import (
    HealthResponse,
    DocumentResponse,
    DocumentListResponse,
    SearchResponse,
    SearchResult,
    ErrorResponse
)

__all__ = [
    # Requests
    "SearchRequest",
    "DocumentUploadRequest",

    # Responses
    "HealthResponse",
    "DocumentResponse",
    "DocumentListResponse",
    "SearchResponse",
    "SearchResult",
    "ErrorResponse",
]
