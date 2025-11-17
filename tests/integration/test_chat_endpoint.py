"""
Integration tests for the chat endpoint.

These tests verify the chat/conversation functionality including:
    - Message processing and response generation
    - Query logging integration
    - Source citation handling
    - Conversation history management
    - Error handling

Test Coverage:
    - POST /api/chat - Send message and get response
    - GET /api/chat/conversations/{id} - Get conversation history
    - DELETE /api/chat/conversations/{id} - Clear conversation
    - Query logging and analytics
    - Source reference formatting
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.api.main import app
from src.api import dependencies

# Create test client
client = TestClient(app, raise_server_exceptions=True)

# Create mock services for dependency injection
mock_vector_store = Mock()
mock_document_registry = AsyncMock()
mock_query_logger = AsyncMock()

# Configure mock vector store with realistic search results
mock_vector_store.search = AsyncMock(return_value=[
    {
        "id": "doc_001_chunk_042",
        "text": "Aragorn, son of Arathorn, stepped forward. He was a ranger of the North.",
        "score": 0.95,
        "metadata": {
            "document_id": "doc_001",
            "page": 42,
            "chapter": "Book 1, Chapter 3"
        }
    },
    {
        "id": "doc_001_chunk_100",
        "text": "Aragorn was revealed to be the heir of Isildur.",
        "score": 0.87,
        "metadata": {
            "document_id": "doc_001",
            "page": 100,
            "chapter": "Book 2, Chapter 1"
        }
    }
])

# Configure mock document registry
mock_doc_record = Mock()
mock_doc_record.id = "doc_001"
mock_doc_record.filename = "fellowship.pdf"
mock_doc_record.pages = 432
mock_document_registry.get_by_id = AsyncMock(return_value=mock_doc_record)

# Configure mock query logger
mock_query_logger.log_query = AsyncMock(return_value=1)  # Returns query_id
mock_query_logger.log_response = AsyncMock()
mock_query_logger.get_by_session = AsyncMock(return_value=[])
mock_query_logger.clear_session = AsyncMock()

# Override dependencies to use mocks
app.dependency_overrides[dependencies.get_vector_store] = lambda: mock_vector_store
app.dependency_overrides[dependencies.get_document_registry] = lambda: mock_document_registry
app.dependency_overrides[dependencies.get_query_logger] = lambda: mock_query_logger


class TestChatEndpoint:
    """Tests for the main chat endpoint."""

    def test_chat_basic_request(self):
        """Test basic chat request with valid message."""
        request_data = {
            "message": "Who is Aragorn?",
            "conversation_id": "test_session_001",
            "user_id": "test_user"
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "response" in data
        assert "sources" in data
        assert "conversation_id" in data
        assert "agent_used" in data
        assert "processing_time_ms" in data

        # Verify values
        assert data["conversation_id"] == request_data["conversation_id"]
        assert isinstance(data["sources"], list)
        assert isinstance(data["processing_time_ms"], (int, float))
        assert data["processing_time_ms"] >= 0

    def test_chat_with_sources(self):
        """Test chat response includes source citations."""
        request_data = {
            "message": "Tell me about Aragorn",
            "conversation_id": "test_session_002"
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Should have sources from mock vector store
        sources = data["sources"]
        assert len(sources) > 0

        # Verify source structure
        source = sources[0]
        assert "document_id" in source
        assert "document_title" in source
        assert "chunk_id" in source
        assert "text" in source
        assert "relevance_score" in source

        # Verify source data
        assert source["document_id"] == "doc_001"
        assert source["document_title"] == "fellowship.pdf"
        assert 0.0 <= source["relevance_score"] <= 1.0

    def test_chat_empty_message(self):
        """Test chat with empty message fails validation."""
        request_data = {
            "message": "",
            "conversation_id": "test_session_003"
        }

        response = client.post("/api/chat", json=request_data)

        # Should fail validation (400 or 422)
        assert response.status_code in [400, 422]

    def test_chat_missing_conversation_id(self):
        """Test chat with missing conversation_id fails validation."""
        request_data = {
            "message": "Test message"
            # Missing conversation_id
        }

        response = client.post("/api/chat", json=request_data)

        # Should fail validation
        assert response.status_code == 422

    def test_chat_with_context(self):
        """Test chat with optional context parameter."""
        request_data = {
            "message": "Who is Gandalf?",
            "conversation_id": "test_session_004",
            "context": {
                "documents": ["doc_001"],
                "mode": "explanatory"
            }
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify metadata includes context info
        assert "metadata" in data
        assert data["metadata"] is not None

    def test_chat_query_logging(self):
        """Test that chat requests are logged to QueryLogger."""
        request_data = {
            "message": "Test query logging",
            "conversation_id": "test_session_005",
            "user_id": "test_user"
        }

        # Reset mock call history
        mock_query_logger.log_query.reset_mock()
        mock_query_logger.log_response.reset_mock()

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200

        # Verify query was logged
        mock_query_logger.log_query.assert_called_once()
        call_args = mock_query_logger.log_query.call_args

        # Verify log_query arguments
        assert call_args.kwargs["session_id"] == request_data["conversation_id"]
        assert call_args.kwargs["query"] == request_data["message"]
        assert call_args.kwargs["user_id"] == request_data["user_id"]

        # Verify response was logged
        mock_query_logger.log_response.assert_called_once()

    def test_chat_long_message(self):
        """Test chat with long message."""
        long_message = "A" * 5000  # 5000 characters

        request_data = {
            "message": long_message,
            "conversation_id": "test_session_006"
        }

        response = client.post("/api/chat", json=request_data)

        # Should accept messages up to 10,000 characters
        assert response.status_code == 200

    def test_chat_too_long_message(self):
        """Test chat with message exceeding max length."""
        too_long_message = "A" * 10001  # Exceeds 10,000 char limit

        request_data = {
            "message": too_long_message,
            "conversation_id": "test_session_007"
        }

        response = client.post("/api/chat", json=request_data)

        # Should fail validation
        assert response.status_code == 422


class TestConversationHistory:
    """Tests for conversation history management."""

    def test_get_conversation_history(self):
        """Test retrieving conversation history."""
        conversation_id = "test_session_100"

        # Configure mock to return sample history
        from src.database.query_logger import QueryRecord
        mock_history = [
            QueryRecord(
                id=1,
                session_id=conversation_id,
                user_id="test_user",
                query="Who is Aragorn?",
                query_type="question",
                response="Aragorn is a ranger...",
                sources='[{"document_id": "doc_001"}]',
                agent_used="retrieval",
                processing_time_ms=1234,
                success=1,
                error_message=None,
                timestamp=datetime.now(datetime.UTC).isoformat(),
                metadata=None
            )
        ]
        mock_query_logger.get_by_session.return_value = mock_history

        response = client.get(f"/api/chat/conversations/{conversation_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "conversation_id" in data
        assert "messages" in data
        assert "total_messages" in data
        assert "returned" in data

        # Verify conversation data
        assert data["conversation_id"] == conversation_id
        assert isinstance(data["messages"], list)

    def test_get_conversation_history_with_limit(self):
        """Test retrieving conversation history with limit."""
        conversation_id = "test_session_101"

        response = client.get(
            f"/api/chat/conversations/{conversation_id}?limit=10"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify limit was applied (check mock was called with limit)
        mock_query_logger.get_by_session.assert_called_with(
            session_id=conversation_id,
            limit=10
        )

    def test_get_empty_conversation_history(self):
        """Test retrieving history for conversation with no messages."""
        conversation_id = "empty_session"

        # Configure mock to return empty list
        mock_query_logger.get_by_session.return_value = []

        response = client.get(f"/api/chat/conversations/{conversation_id}")

        assert response.status_code == 200
        data = response.json()

        # Should return empty messages list
        assert data["total_messages"] == 0
        assert data["messages"] == []


class TestConversationManagement:
    """Tests for conversation management operations."""

    def test_clear_conversation(self):
        """Test clearing/deleting a conversation."""
        conversation_id = "test_session_200"

        # Reset mock call history
        mock_query_logger.clear_session.reset_mock()

        response = client.delete(f"/api/chat/conversations/{conversation_id}")

        # Should return 204 No Content
        assert response.status_code == 204

        # Verify clear_session was called
        mock_query_logger.clear_session.assert_called_once_with(conversation_id)

    def test_clear_nonexistent_conversation(self):
        """Test clearing a conversation that doesn't exist."""
        conversation_id = "nonexistent_session"

        # Should still succeed (idempotent operation)
        response = client.delete(f"/api/chat/conversations/{conversation_id}")

        assert response.status_code == 204


class TestChatErrorHandling:
    """Tests for chat error handling."""

    def test_chat_vector_store_error(self):
        """Test chat handling when vector store fails."""
        # Configure mock to raise exception
        mock_vector_store.search.side_effect = Exception("Vector store error")

        request_data = {
            "message": "Test error handling",
            "conversation_id": "error_session_001"
        }

        response = client.post("/api/chat", json=request_data)

        # Should return 500 error
        assert response.status_code == 500
        data = response.json()

        # Verify error response structure
        assert "detail" in data
        detail = data["detail"]
        assert detail["error"] == "ChatError"

        # Reset mock
        mock_vector_store.search.side_effect = None

    def test_chat_query_logger_error(self):
        """Test chat handling when query logger fails."""
        # Configure mock to raise exception
        mock_query_logger.log_query.side_effect = Exception("Logger error")

        request_data = {
            "message": "Test logger error",
            "conversation_id": "error_session_002"
        }

        response = client.post("/api/chat", json=request_data)

        # Should return 500 error
        assert response.status_code == 500

        # Reset mock
        mock_query_logger.log_query.side_effect = None


class TestChatMetadata:
    """Tests for chat metadata and tracking."""

    def test_chat_includes_processing_time(self):
        """Test chat response includes processing time."""
        request_data = {
            "message": "Test timing",
            "conversation_id": "timing_session"
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify processing time is included and reasonable
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] > 0
        assert data["processing_time_ms"] < 10000  # Should be under 10 seconds

    def test_chat_includes_agent_info(self):
        """Test chat response includes agent information."""
        request_data = {
            "message": "Test agent info",
            "conversation_id": "agent_session"
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify agent information is included
        assert "agent_used" in data
        # Phase 2: Should use "retrieval" agent
        assert data["agent_used"] == "retrieval"

    def test_chat_metadata_field(self):
        """Test chat response includes metadata field."""
        request_data = {
            "message": "Test metadata",
            "conversation_id": "metadata_session"
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify metadata is included
        assert "metadata" in data
        metadata = data["metadata"]

        # Verify metadata structure
        assert "phase" in metadata
        assert "implementation" in metadata
        assert metadata["phase"] == "2"
        assert metadata["implementation"] == "basic_rag"


# Cleanup: Reset dependency overrides after all tests
def teardown_module():
    """Clean up test fixtures after all tests in module."""
    app.dependency_overrides.clear()
