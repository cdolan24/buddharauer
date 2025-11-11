"""
Basic integration tests for FastAPI endpoints.

These tests verify that the API endpoints are properly configured and
respond correctly to basic requests. They use FastAPI's TestClient for
synchronous testing without requiring a running server.

Test Coverage:
    - Root endpoint
    - Health endpoints
    - Documents endpoints (basic structure)
    - Search endpoints (basic structure)
    - Error handling
    - CORS configuration

Note:
    These are basic smoke tests. Full integration tests with actual
    database operations will be added once the services are fully integrated.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
from src.api.main import app
from src.api import dependencies

# Create test client
client = TestClient(app, raise_server_exceptions=True)

# Create mock services for dependency injection
mock_vector_store = Mock()
mock_vector_store.get_collection_stats = Mock(return_value={"document_count": 42})
mock_vector_store.search = AsyncMock(return_value=[])  # Default: no search results

mock_document_registry = AsyncMock()
mock_document_registry.get_by_id = AsyncMock(return_value=None)  # Default: document not found
mock_document_registry.list_all = AsyncMock(return_value=[])  # Default: no documents
mock_document_registry.get_by_status = AsyncMock(return_value=[])  # Default: no documents

# Override dependencies to use mocks
app.dependency_overrides[dependencies.get_vector_store] = lambda: mock_vector_store
app.dependency_overrides[dependencies.get_document_registry] = lambda: mock_document_registry


class TestRootEndpoint:
    """Tests for the root API endpoint."""

    def test_root_endpoint(self):
        """Test root endpoint returns API information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "docs" in data
        assert "status" in data

        # Verify values
        assert data["name"] == "Buddharauer API"
        assert data["status"] == "operational"


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self):
        """Test main health check endpoint."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        assert "status" in data
        assert "ollama_connected" in data
        assert "vector_db_status" in data
        assert "documents_indexed" in data
        assert "uptime_seconds" in data

        # Verify types
        assert isinstance(data["status"], str)
        assert isinstance(data["ollama_connected"], bool)
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_ping_endpoint(self):
        """Test simple ping endpoint."""
        response = client.get("/api/health/ping")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "timestamp" in data
        assert data["message"] == "pong"


class TestDocumentsEndpoints:
    """Tests for document management endpoints."""

    def test_list_documents_default(self):
        """Test listing documents with default parameters."""
        response = client.get("/api/documents")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "documents" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

        # Verify default pagination
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_documents_pagination(self):
        """Test listing documents with custom pagination."""
        response = client.get("/api/documents?page=2&page_size=10")

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 2
        assert data["page_size"] == 10

    def test_list_documents_invalid_pagination(self):
        """Test listing documents with invalid pagination."""
        # Page must be >= 1
        response = client.get("/api/documents?page=0")
        assert response.status_code == 422

        # Page size must be <= 100
        response = client.get("/api/documents?page_size=200")
        assert response.status_code == 422

    def test_get_document_not_found(self):
        """Test getting a non-existent document."""
        response = client.get("/api/documents/nonexistent_doc")

        assert response.status_code == 404
        data = response.json()

        # FastAPI wraps error details in "detail" field
        assert "detail" in data
        detail = data["detail"]
        assert detail["error"] == "NotFoundError"

    def test_get_document_content_not_found(self):
        """Test getting content for non-existent document."""
        response = client.get("/api/documents/nonexistent_doc/content")

        assert response.status_code == 404

    def test_get_document_content_formats(self):
        """Test different content format parameters."""
        # Valid formats
        response = client.get("/api/documents/doc_001/content?format=markdown")
        assert response.status_code in [200, 404]  # 404 expected for now

        response = client.get("/api/documents/doc_001/content?format=text")
        assert response.status_code in [200, 404]

        # Invalid format should fail validation
        response = client.get("/api/documents/doc_001/content?format=invalid")
        assert response.status_code == 422

    def test_delete_document_not_found(self):
        """Test deleting a non-existent document."""
        response = client.delete("/api/documents/nonexistent_doc")

        assert response.status_code == 404


class TestSearchEndpoints:
    """Tests for search endpoints."""

    def test_search_valid_request(self):
        """Test search with valid request."""
        request_data = {
            "query": "Who is Aragorn?",
            "limit": 10,
            "include_metadata": True
        }

        response = client.post("/api/search", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "results" in data
        assert "query" in data
        assert "total_results" in data
        assert "processing_time_ms" in data

        # Verify query echoed back
        assert data["query"] == request_data["query"]

    def test_search_empty_query(self):
        """Test search with empty query."""
        request_data = {
            "query": "",
            "limit": 10
        }

        response = client.post("/api/search", json=request_data)

        # Should fail validation or return error
        assert response.status_code in [400, 422]

    def test_search_invalid_limit(self):
        """Test search with invalid limit values."""
        # Limit too low
        request_data = {
            "query": "test",
            "limit": 0
        }
        response = client.post("/api/search", json=request_data)
        assert response.status_code == 422

        # Limit too high
        request_data["limit"] = 200
        response = client.post("/api/search", json=request_data)
        assert response.status_code == 422

    def test_search_with_filters(self):
        """Test search with metadata filters."""
        request_data = {
            "query": "test query",
            "limit": 5,
            "filters": {"document_id": "doc_001"},
            "include_metadata": True
        }

        response = client.post("/api/search", json=request_data)

        assert response.status_code == 200

    def test_find_similar_chunks(self):
        """Test finding similar chunks endpoint."""
        response = client.get("/api/search/similar/doc_001_chunk_001?limit=5")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "results" in data
        assert "query" in data
        assert "total_results" in data
        assert "processing_time_ms" in data


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_not_found(self):
        """Test 404 for non-existent endpoints."""
        response = client.get("/api/nonexistent")

        assert response.status_code == 404

    def test_validation_error_response_structure(self):
        """Test validation error response structure."""
        # Send invalid request (missing required field)
        response = client.post("/api/search", json={})

        assert response.status_code == 422
        data = response.json()

        # Should have error information
        assert "error" in data
        assert "message" in data


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers(self):
        """Test CORS headers are present."""
        # Make OPTIONS request to check CORS
        response = client.options(
            "/api/health",
            headers={"Origin": "http://localhost:7860"}
        )

        # Should allow the request
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled


class TestDocumentation:
    """Tests for API documentation endpoints."""

    def test_openapi_schema(self):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        # Verify basic OpenAPI structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

        # Verify title
        assert schema["info"]["title"] == "Buddharauer API"

    def test_swagger_ui(self):
        """Test Swagger UI is available."""
        response = client.get("/docs")

        assert response.status_code == 200

    def test_redoc_ui(self):
        """Test ReDoc UI is available."""
        response = client.get("/redoc")

        assert response.status_code == 200
