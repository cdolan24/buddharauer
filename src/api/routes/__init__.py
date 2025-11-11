"""
API route definitions for Buddharauer REST API.

This package contains all endpoint implementations organized by domain:
    - health: System health and status checks
    - documents: Document management (CRUD operations)
    - search: Vector search operations
    - chat: Conversational AI interface with document retrieval

Each route module is a FastAPI APIRouter that can be mounted to the main app.
"""

from .health import router as health_router
from .documents import router as documents_router
from .search import router as search_router
from .chat import router as chat_router

__all__ = [
    "health_router",
    "documents_router",
    "search_router",
    "chat_router",
]
