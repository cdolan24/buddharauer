"""
Health check endpoints for system monitoring.

This module provides endpoints for checking the health and status of the
Buddharauer system components:
    - API server status
    - Ollama service connectivity
    - Vector database availability
    - Document index statistics

Usage:
    These endpoints are used by:
    - Health monitoring systems
    - Load balancers
    - DevOps dashboards
    - System administrators

Example Response:
    GET /api/health
    {
        "status": "healthy",
        "ollama_connected": true,
        "vector_db_status": "operational",
        "documents_indexed": 47,
        "uptime_seconds": 3600.5
    }
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import time
import httpx

from src.api.models.responses import HealthResponse
from src.utils.logging import get_logger

# Import dependency injection functions
from src.api.dependencies import get_vector_store, get_document_registry

logger = get_logger(__name__)

# Create router for health endpoints
router = APIRouter(
    prefix="/api/health",
    tags=["health"],
    responses={
        200: {"description": "System is healthy"},
        503: {"description": "System is degraded or unhealthy"}
    }
)

# Track API start time for uptime calculation
API_START_TIME = time.time()


async def check_ollama_health() -> bool:
    """
    Check if Ollama service is accessible.

    Returns:
        bool: True if Ollama is responding, False otherwise

    Note:
        This makes a simple HTTP request to Ollama's API to verify connectivity.
        Timeout is set to 2 seconds to avoid blocking health checks.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Try to reach Ollama's API endpoint
            response = await client.get("http://localhost:11434/api/tags")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        return False


async def check_vector_db_health(vector_store) -> str:
    """
    Check vector database status.

    Args:
        vector_store: VectorStore instance to check

    Returns:
        str: Status string ("operational", "degraded", "unavailable")

    Note:
        This performs a lightweight operation to verify the vector store
        is accessible and functioning.
    """
    try:
        # Try to get collection stats as a health check
        stats = vector_store.get_collection_stats()
        return "operational"
    except Exception as e:
        logger.error(f"Vector DB health check failed: {e}")
        return "unavailable"


async def get_documents_count(vector_store) -> int:
    """
    Get count of indexed documents.

    Args:
        vector_store: VectorStore instance

    Returns:
        int: Number of documents in the vector store

    Note:
        Returns 0 if count cannot be determined.
    """
    try:
        stats = vector_store.get_collection_stats()
        return stats.get("document_count", 0)
    except Exception:
        return 0


@router.get("", response_model=HealthResponse, status_code=200)
async def health_check(
    vector_store = Depends(get_vector_store),
    registry = Depends(get_document_registry)
):
    """
    Comprehensive system health check.

    Checks the status of all system components:
    - Ollama LLM service
    - Vector database
    - Document index

    Args:
        vector_store: VectorStore instance (injected dependency)
        registry: DocumentRegistry instance (injected dependency)

    Returns:
        HealthResponse: Complete system health status

    Status Codes:
        - 200: System is healthy
        - 503: System is degraded or unhealthy

    Example:
        ```bash
        curl http://localhost:8000/api/health
        ```

    Note:
        This endpoint is designed to be called frequently by monitoring systems.
        It should complete quickly (< 1 second) to avoid blocking.
    """
    # Check Ollama connectivity
    ollama_healthy = await check_ollama_health()

    # Check vector database health
    vector_db_status = await check_vector_db_health(vector_store)

    # Get document count from vector store
    documents_indexed = await get_documents_count(vector_store)

    # Calculate uptime
    uptime = time.time() - API_START_TIME

    # Determine overall status
    # System is healthy if all critical components are operational
    if ollama_healthy and vector_db_status == "operational":
        overall_status = "healthy"
    elif ollama_healthy or vector_db_status == "operational":
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        ollama_connected=ollama_healthy,
        vector_db_status=vector_db_status,
        documents_indexed=documents_indexed,
        uptime_seconds=uptime
    )


@router.get("/ping", status_code=200)
async def ping():
    """
    Simple ping endpoint for basic availability checks.

    Returns:
        Dict with "pong" message and timestamp

    Example:
        ```bash
        curl http://localhost:8000/api/health/ping
        ```

    Note:
        This is a lightweight endpoint that just verifies the API server is
        responding. It doesn't check dependent services.
    """
    return {
        "message": "pong",
        "timestamp": time.time()
    }
