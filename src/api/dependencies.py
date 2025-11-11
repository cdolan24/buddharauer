"""
Dependency injection functions for FastAPI routes.

This module provides FastAPI dependency functions that give routes access to
shared services like VectorStore, DocumentRegistry, and QueryLogger.

The dependencies are initialized during application startup in main.py and
stored in app_state. These functions retrieve the initialized instances.

Usage in routes:
    ```python
    from fastapi import Depends
    from src.api.dependencies import get_vector_store

    @router.get("/some-endpoint")
    async def my_endpoint(vector_store = Depends(get_vector_store)):
        results = await vector_store.search(...)
        return results
    ```

See Also:
    - src.api.main: Application initialization and lifespan management
    - src.database.vector_store: VectorStore implementation
    - src.database.document_registry: DocumentRegistry implementation
    - src.database.query_logger: QueryLogger implementation
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.vector_store import VectorStore
    from src.database.document_registry import DocumentRegistry
    from src.database.query_logger import QueryLogger

# Import app_state from main
# This works because app_state is a module-level variable, not a class/function
from src.api import main


def get_vector_store() -> "VectorStore":
    """
    Dependency injection for VectorStore.

    Returns:
        VectorStore instance from application state

    Raises:
        RuntimeError: If vector store not initialized

    Usage:
        ```python
        from fastapi import Depends
        from src.api.dependencies import get_vector_store

        @router.get("/search")
        async def search(vector_store = Depends(get_vector_store)):
            results = await vector_store.search(query="example")
            return results
        ```

    Note:
        This function is called automatically by FastAPI when used as a dependency.
        The VectorStore instance is initialized during application startup.
    """
    if main.app_state.get("vector_store") is None:
        raise RuntimeError("Vector store not initialized")
    return main.app_state["vector_store"]


def get_document_registry() -> "DocumentRegistry":
    """
    Dependency injection for DocumentRegistry.

    Returns:
        DocumentRegistry instance from application state

    Raises:
        RuntimeError: If document registry not initialized

    Usage:
        ```python
        from fastapi import Depends
        from src.api.dependencies import get_document_registry

        @router.get("/documents")
        async def list_docs(registry = Depends(get_document_registry)):
            docs = await registry.list_all()
            return docs
        ```

    Note:
        This function is called automatically by FastAPI when used as a dependency.
        The DocumentRegistry instance is initialized during application startup.
    """
    if main.app_state.get("document_registry") is None:
        raise RuntimeError("Document registry not initialized")
    return main.app_state["document_registry"]


def get_query_logger() -> "QueryLogger":
    """
    Dependency injection for QueryLogger.

    Returns:
        QueryLogger instance from application state

    Raises:
        RuntimeError: If query logger not initialized

    Usage:
        ```python
        from fastapi import Depends
        from src.api.dependencies import get_query_logger

        @router.post("/chat")
        async def chat(query_logger = Depends(get_query_logger)):
            query_id = await query_logger.log_query(...)
            return {"query_id": query_id}
        ```

    Note:
        This function is called automatically by FastAPI when used as a dependency.
        The QueryLogger instance is initialized during application startup.
    """
    if main.app_state.get("query_logger") is None:
        raise RuntimeError("Query logger not initialized")
    return main.app_state["query_logger"]
