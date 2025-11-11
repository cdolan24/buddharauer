"""
Main FastAPI application for Buddharauer document analysis system.

This module sets up the FastAPI application with:
    - Route registration
    - CORS middleware
    - Error handling
    - Application lifecycle management
    - Dependency injection for shared services

The API provides REST endpoints for:
    - Document management (upload, list, retrieve, delete)
    - Vector search (semantic search across documents)
    - System health monitoring
    - Future: Chat interface with FastAgent agents

Architecture:
    The API acts as a bridge between the web frontend (Gradio) and the
    document processing pipeline. It provides a RESTful interface while
    maintaining separation of concerns.

Usage:
    # Development server
    uvicorn src.api.main:app --reload --port 8000

    # Production server
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

Example:
    >>> import httpx
    >>>
    >>> # Check API health
    >>> response = httpx.get("http://localhost:8000/api/health")
    >>> print(response.json())
    {'status': 'healthy', 'ollama_connected': True, ...}
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from typing import Dict, Any
import time

from src.api.routes import health_router, documents_router, search_router
from src.utils.logging import get_logger
from src.api.models.responses import ErrorResponse

logger = get_logger(__name__)

# Application state for tracking startup time and shared resources
app_state: Dict[str, Any] = {
    "start_time": time.time(),
    "vector_store": None,  # Will be initialized in lifespan
    "document_registry": None,  # Will be initialized in lifespan
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown logic.

    Startup:
        - Initialize vector store
        - Initialize document registry
        - Load configuration
        - Setup monitoring

    Shutdown:
        - Close database connections
        - Flush metrics
        - Cleanup resources

    Args:
        app: FastAPI application instance

    Yields:
        Control to application runtime
    """
    # Startup
    logger.info("Starting Buddharauer API...")

    try:
        # TODO: Initialize VectorStore
        # from src.database.vector_store import VectorStore
        # app_state["vector_store"] = VectorStore("./vector_db")
        # logger.info("Vector store initialized")

        # TODO: Initialize DocumentRegistry
        # from src.database.document_registry import DocumentRegistry
        # app_state["document_registry"] = DocumentRegistry()
        # logger.info("Document registry initialized")

        logger.info("API startup complete")

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down Buddharauer API...")

    try:
        # TODO: Cleanup resources
        # if app_state.get("vector_store"):
        #     app_state["vector_store"].close()

        logger.info("API shutdown complete")

    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="Buddharauer API",
    description="REST API for local-first document analysis with FastAgent",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# Configure CORS
# Allow Gradio frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:7860",  # Gradio default port
        "http://localhost:7861",  # Alternative Gradio port
        "http://127.0.0.1:7860",
        "http://127.0.0.1:7861",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with detailed error messages.

    Args:
        request: The request that caused the error
        exc: Validation exception with details

    Returns:
        JSONResponse with error details
    """
    logger.warning(f"Validation error on {request.url}: {exc}")

    # Extract first error for simplicity
    error_details = exc.errors()[0] if exc.errors() else {}

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            details={
                "field": ".".join(str(loc) for loc in error_details.get("loc", [])),
                "message": error_details.get("msg", "Invalid input"),
                "type": error_details.get("type", "unknown")
            }
        ).model_dump()
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions with logging.

    Args:
        request: The request that caused the error
        exc: The exception

    Returns:
        JSONResponse with error message
    """
    logger.error(
        f"Unhandled exception on {request.url}: {exc}",
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            details={"path": str(request.url)}
        ).model_dump()
    )


# Register routers
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(search_router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with API information.

    Returns:
        Dict with API metadata and links

    Example:
        ```bash
        curl http://localhost:8000/
        ```

    Response:
        ```json
        {
            "name": "Buddharauer API",
            "version": "0.1.0",
            "docs": "http://localhost:8000/docs",
            "status": "operational"
        }
        ```
    """
    return {
        "name": "Buddharauer API",
        "version": "0.1.0",
        "description": "Local-first document analysis with FastAgent",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health",
        "status": "operational"
    }


# Utility function to get shared services (for dependency injection)
def get_vector_store():
    """
    Dependency injection for VectorStore.

    Returns:
        VectorStore instance from application state

    Raises:
        RuntimeError: If vector store not initialized

    Usage:
        ```python
        @app.get("/some-endpoint")
        async def endpoint(vector_store = Depends(get_vector_store)):
            results = vector_store.search(...)
            return results
        ```
    """
    if app_state.get("vector_store") is None:
        raise RuntimeError("Vector store not initialized")
    return app_state["vector_store"]


def get_document_registry():
    """
    Dependency injection for DocumentRegistry.

    Returns:
        DocumentRegistry instance from application state

    Raises:
        RuntimeError: If document registry not initialized

    Usage:
        ```python
        @app.get("/some-endpoint")
        async def endpoint(registry = Depends(get_document_registry)):
            docs = registry.list_all()
            return docs
        ```
    """
    if app_state.get("document_registry") is None:
        raise RuntimeError("Document registry not initialized")
    return app_state["document_registry"]


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting development server...")
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
