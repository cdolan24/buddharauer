"""
Unit tests for Retrieval Agent.

Tests the RetrievalAgent class including initialization, search functionality,
query reformulation, and result re-ranking.

Test Coverage:
    - Agent initialization
    - Vector search operations
    - Result formatting and enrichment
    - Query reformulation
    - Result re-ranking
    - Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import asdict

# Import module under test
from src.agents.retrieval import (
    RetrievalAgent,
    SearchResult,
    create_retrieval_agent,
    vector_search_tool
)


class TestRetrievalAgentInitialization:
    """Tests for Retrieval Agent initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        agent = RetrievalAgent()

        assert agent.model == "generic.qwen2.5:latest"
        assert agent.temperature == 0.5
        assert agent.vector_store is not None
        assert agent.document_registry is not None
        assert agent.agent is None  # Not initialized yet

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        agent = RetrievalAgent(
            model="generic.custom:latest",
            temperature=0.7
        )

        assert agent.model == "generic.custom:latest"
        assert agent.temperature == 0.7

    def test_init_with_custom_dependencies(self):
        """Test initialization with custom vector store and registry."""
        mock_vector_store = Mock()
        mock_registry = Mock()

        agent = RetrievalAgent(
            vector_store=mock_vector_store,
            document_registry=mock_registry
        )

        assert agent.vector_store == mock_vector_store
        assert agent.document_registry == mock_registry

    @patch('src.agents.retrieval.FASTAGENT_AVAILABLE', True)
    @patch('src.agents.retrieval.Agent')
    @patch('src.agents.retrieval.initialize_fastagent')
    @pytest.mark.asyncio
    async def test_initialize_agent(self, mock_init_fa, mock_agent_class):
        """Test agent initialization process."""
        # Mock Agent class
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        agent = RetrievalAgent()
        result = await agent.initialize()

        # Should successfully initialize
        assert result is True
        assert agent.agent == mock_agent_instance

        # Verify FastAgent initialization called
        mock_init_fa.assert_called_once_with(verify_connection=True)

        # Verify Agent created with correct parameters
        mock_agent_class.assert_called_once()
        call_kwargs = mock_agent_class.call_args.kwargs
        assert call_kwargs["name"] == "retrieval"
        assert call_kwargs["model"] == "generic.qwen2.5:latest"
        assert call_kwargs["temperature"] == 0.5
        assert "system_prompt" in call_kwargs

    @patch('src.agents.retrieval.FASTAGENT_AVAILABLE', False)
    @pytest.mark.asyncio
    async def test_initialize_without_fastagent(self):
        """Test initialization when FastAgent not available."""
        agent = RetrievalAgent()
        result = await agent.initialize()

        assert result is False
        assert agent.agent is None


class TestSearchFunctionality:
    """Tests for search operations."""

    @pytest.mark.asyncio
    async def test_search_basic(self):
        """Test basic search functionality."""
        # Mock vector store
        mock_vector_store = AsyncMock()
        mock_vector_store.search = AsyncMock(return_value=[
            {
                "id": "doc_001_chunk_042",
                "text": "Aragorn was a ranger of the North.",
                "score": 0.95,
                "metadata": {
                    "document_id": "doc_001",
                    "page": 42
                }
            },
            {
                "id": "doc_001_chunk_100",
                "text": "Aragorn became king of Gondor.",
                "score": 0.87,
                "metadata": {
                    "document_id": "doc_001",
                    "page": 100
                }
            }
        ])

        # Mock document registry
        mock_doc_record = Mock()
        mock_doc_record.filename = "fellowship.pdf"
        mock_registry = AsyncMock()
        mock_registry.get_by_id = AsyncMock(return_value=mock_doc_record)

        # Create agent
        agent = RetrievalAgent(
            vector_store=mock_vector_store,
            document_registry=mock_registry
        )

        # Perform search
        results = await agent.search("Who is Aragorn?", limit=5)

        # Verify results
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

        # Check first result
        result1 = results[0]
        assert result1.chunk_id == "doc_001_chunk_042"
        assert result1.document_id == "doc_001"
        assert result1.document_title == "fellowship.pdf"
        assert result1.text == "Aragorn was a ranger of the North."
        assert result1.score == 0.95
        assert result1.page == 42

        # Verify vector store called correctly
        mock_vector_store.search.assert_called_once_with(
            query_texts=["Who is Aragorn?"],
            n_results=5,
            where=None
        )

    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        """Test search with metadata filters."""
        mock_vector_store = AsyncMock()
        mock_vector_store.search = AsyncMock(return_value=[])
        mock_registry = AsyncMock()

        agent = RetrievalAgent(
            vector_store=mock_vector_store,
            document_registry=mock_registry
        )

        # Search with filters
        filters = {"document_id": "doc_001"}
        await agent.search("query", limit=3, filters=filters)

        # Verify filters passed to vector store
        call_args = mock_vector_store.search.call_args
        assert call_args.kwargs["where"] == filters
        assert call_args.kwargs["n_results"] == 3

    @pytest.mark.asyncio
    async def test_search_with_min_score(self):
        """Test search with minimum score filtering."""
        mock_vector_store = AsyncMock()
        mock_vector_store.search = AsyncMock(return_value=[
            {
                "id": "chunk_high",
                "text": "High score result",
                "score": 0.95,
                "metadata": {"document_id": "doc_001"}
            },
            {
                "id": "chunk_low",
                "text": "Low score result",
                "score": 0.3,
                "metadata": {"document_id": "doc_001"}
            }
        ])

        mock_doc_record = Mock()
        mock_doc_record.filename = "doc.pdf"
        mock_registry = AsyncMock()
        mock_registry.get_by_id = AsyncMock(return_value=mock_doc_record)

        agent = RetrievalAgent(
            vector_store=mock_vector_store,
            document_registry=mock_registry
        )

        # Search with minimum score threshold
        results = await agent.search("query", min_score=0.5)

        # Should only return high-score result
        assert len(results) == 1
        assert results[0].score == 0.95

    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        """Test search handles errors gracefully."""
        mock_vector_store = AsyncMock()
        mock_vector_store.search = AsyncMock(side_effect=Exception("DB error"))

        agent = RetrievalAgent(vector_store=mock_vector_store)

        # Should raise FastAgentError
        from src.utils.fastagent_client import FastAgentError
        with pytest.raises(FastAgentError, match="Search operation failed"):
            await agent.search("query")

    @pytest.mark.asyncio
    async def test_search_registry_failure(self):
        """Test search continues when document registry fails."""
        mock_vector_store = AsyncMock()
        mock_vector_store.search = AsyncMock(return_value=[
            {
                "id": "chunk_001",
                "text": "Test text",
                "score": 0.9,
                "metadata": {"document_id": "doc_001"}
            }
        ])

        # Mock registry that fails
        mock_registry = AsyncMock()
        mock_registry.get_by_id = AsyncMock(side_effect=Exception("Registry error"))

        agent = RetrievalAgent(
            vector_store=mock_vector_store,
            document_registry=mock_registry
        )

        # Search should still work, but with "unknown" title
        results = await agent.search("query")

        assert len(results) == 1
        assert results[0].document_title == "unknown"


class TestQueryReformulation:
    """Tests for query reformulation."""

    @pytest.mark.asyncio
    async def test_reformulate_query_without_agent(self):
        """Test query reformulation without initialized agent."""
        agent = RetrievalAgent()

        # Should return original query
        original = "Who is Aragorn?"
        reformulated = await agent.reformulate_query(original)

        assert reformulated == original

    @pytest.mark.asyncio
    async def test_reformulate_query_with_agent(self):
        """Test query reformulation with agent (placeholder)."""
        agent = RetrievalAgent()
        agent.agent = Mock()  # Mock agent

        original = "Who is Aragorn?"
        reformulated = await agent.reformulate_query(original)

        # Currently returns original (placeholder implementation)
        assert reformulated == original


class TestResultReranking:
    """Tests for result re-ranking."""

    @pytest.mark.asyncio
    async def test_rerank_results_without_agent(self):
        """Test re-ranking without initialized agent."""
        agent = RetrievalAgent()

        # Create test results
        results = [
            SearchResult("chunk1", "doc1", "text1", 0.8, None, None, None),
            SearchResult("chunk2", "doc1", "text2", 0.9, None, None, None),
            SearchResult("chunk3", "doc1", "text3", 0.7, None, None, None),
        ]

        reranked = await agent.rerank_results("query", results)

        # Should be sorted by score (descending)
        assert reranked[0].score == 0.9
        assert reranked[1].score == 0.8
        assert reranked[2].score == 0.7

    @pytest.mark.asyncio
    async def test_rerank_results_with_limit(self):
        """Test re-ranking with result limit."""
        agent = RetrievalAgent()

        results = [
            SearchResult("chunk1", "doc1", "text1", 0.8, None, None, None),
            SearchResult("chunk2", "doc1", "text2", 0.9, None, None, None),
            SearchResult("chunk3", "doc1", "text3", 0.7, None, None, None),
        ]

        reranked = await agent.rerank_results("query", results, limit=2)

        # Should return top 2 results
        assert len(reranked) == 2
        assert reranked[0].score == 0.9
        assert reranked[1].score == 0.8

    @pytest.mark.asyncio
    async def test_rerank_empty_results(self):
        """Test re-ranking with empty results list."""
        agent = RetrievalAgent()

        reranked = await agent.rerank_results("query", [])

        assert reranked == []


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_to_dict_conversion(self):
        """Test converting search results to dictionary format."""
        agent = RetrievalAgent()

        results = [
            SearchResult(
                chunk_id="chunk_001",
                document_id="doc_001",
                text="Sample text",
                score=0.95,
                page=42,
                document_title="test.pdf",
                metadata={"chapter": "1"}
            )
        ]

        dict_results = agent.to_dict(results)

        assert len(dict_results) == 1
        assert dict_results[0]["chunk_id"] == "chunk_001"
        assert dict_results[0]["document_id"] == "doc_001"
        assert dict_results[0]["score"] == 0.95
        assert dict_results[0]["page"] == 42
        assert dict_results[0]["metadata"]["chapter"] == "1"


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test creating SearchResult instance."""
        result = SearchResult(
            chunk_id="chunk_001",
            document_id="doc_001",
            text="Sample text",
            score=0.95,
            page=42,
            document_title="test.pdf",
            metadata={"key": "value"}
        )

        assert result.chunk_id == "chunk_001"
        assert result.document_id == "doc_001"
        assert result.text == "Sample text"
        assert result.score == 0.95
        assert result.page == 42
        assert result.document_title == "test.pdf"
        assert result.metadata == {"key": "value"}

    def test_search_result_optional_fields(self):
        """Test SearchResult with optional fields as None."""
        result = SearchResult(
            chunk_id="chunk_001",
            document_id="doc_001",
            text="Sample text",
            score=0.95
        )

        assert result.page is None
        assert result.document_title is None
        assert result.metadata is None

    def test_search_result_to_dict(self):
        """Test converting SearchResult to dictionary."""
        result = SearchResult(
            chunk_id="chunk_001",
            document_id="doc_001",
            text="Sample text",
            score=0.95,
            page=42
        )

        result_dict = asdict(result)

        assert result_dict["chunk_id"] == "chunk_001"
        assert result_dict["score"] == 0.95


class TestFactoryFunction:
    """Tests for factory function."""

    @patch('src.agents.retrieval.RetrievalAgent')
    @pytest.mark.asyncio
    async def test_create_retrieval_agent(self, mock_agent_class):
        """Test factory function creates and initializes agent."""
        mock_agent_instance = AsyncMock()
        mock_agent_instance.initialize = AsyncMock(return_value=True)
        mock_agent_class.return_value = mock_agent_instance

        agent = await create_retrieval_agent()

        # Verify agent created
        mock_agent_class.assert_called_once_with(
            vector_store=None,
            document_registry=None
        )

        # Verify initialize called
        mock_agent_instance.initialize.assert_called_once()


class TestMCPTools:
    """Tests for MCP tool functions."""

    @pytest.mark.asyncio
    async def test_vector_search_tool(self):
        """Test vector search MCP tool."""
        # This is a basic test - tool would be used by FastAgent
        # We can't fully test without FastAgent integration
        result = await vector_search_tool("test query", limit=3)

        # Should return list (even if empty without real vector store)
        assert isinstance(result, list)
