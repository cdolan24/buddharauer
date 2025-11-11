"""
FastAPI backend for Buddharauer document analysis system.

This package provides a REST API layer for interacting with the document
processing pipeline, vector store, and eventually FastAgent agents.

The API follows RESTful conventions and provides:
    - Document management (upload, list, retrieve)
    - Vector search capabilities
    - System health monitoring
    - Future: Chat interface with FastAgent agents

See Also:
    - main.py: Main FastAPI application setup
    - routes/: Individual endpoint implementations
    - models/: Pydantic models for request/response validation
"""
