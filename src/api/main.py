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
    - Chat interface with FastAgent orchestrator (Phase 3)
    - System health monitoring

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

from src.api.routes import health_router, documents_router, search_router, chat_router
from src.utils.logging import get_logger
from src.api.models.responses import ErrorResponse

logger = get_logger(__name__)

# Application state for tracking startup time and shared resources
# These are initialized during the lifespan startup phase and used for dependency injection
app_state: Dict[str, Any] = {
    "start_time": time.time(),
    "vector_store": None,  # VectorStore instance for semantic search
    "document_registry": None,  # DocumentRegistry for tracking document metadata
    "query_logger": None,  # QueryLogger for tracking user queries and analytics
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
        # Initialize VectorStore for semantic search
        from src.database.vector_store import VectorStore
        app_state["vector_store"] = VectorStore(
            persist_directory="./vector_db",
            collection_name="documents"
        )
        logger.info("Vector store initialized")

        # Initialize DocumentRegistry for tracking document metadata
        from src.database.document_registry import DocumentRegistry
        app_state["document_registry"] = DocumentRegistry("data_storage/documents.db")
        await app_state["document_registry"].initialize()
        logger.info("Document registry initialized")

        # Initialize QueryLogger for tracking user queries
        from src.database.query_logger import QueryLogger
        app_state["query_logger"] = QueryLogger("data_storage/queries.db")
        await app_state["query_logger"].initialize()
        logger.info("Query logger initialized")

        # Initialize FastAgent agents for Phase 3 chat functionality
        try:
            from src.api.routes.chat import initialize_agents
            await initialize_agents(
                vector_store=app_state["vector_store"],
                document_registry=app_state["document_registry"]
            )
            logger.info("FastAgent orchestrator and sub-agents initialized")
        except Exception as agent_error:
            logger.warning(
                f"Agent initialization failed (will use fallback): {agent_error}",
                exc_info=True
            )
            # Continue startup even if agents fail to initialize
            # The chat endpoint will fall back to Phase 2 behavior

        logger.info("API startup complete - all services initialized")

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down Buddharauer API...")

    try:
        # Cleanup VectorStore resources
        # Note: Current VectorStore implementation doesn't require explicit cleanup
        # Future ChromaDB integration may need client.close() or similar
        if app_state.get("vector_store"):
            logger.debug("VectorStore cleanup complete")

        # Cleanup database connections
        # Note: aiosqlite connections are context-managed and auto-closed
        # No explicit cleanup needed for DocumentRegistry or QueryLogger
        if app_state.get("document_registry"):
            logger.debug("DocumentRegistry cleanup complete")
        if app_state.get("query_logger"):
            logger.debug("QueryLogger cleanup complete")

        logger.info("API shutdown complete - all resources cleaned up")

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
app.include_router(chat_router)


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


# Note: Dependency injection functions moved to src/api/dependencies.py
# to avoid circular import issues with routes


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
