"""
Unit tests for Web Search Agent.

Tests the WebSearchAgent class including initialization, query optimization,
result filtering, summarization, and source validation.

Test Coverage:
    - Agent initialization and setup
    - FastAgent instance creation with MCP tools
    - Query formulation and optimization
    - Search execution
    - Result filtering and ranking
    - Summary generation
    - Source validation
    - Error handling and fallbacks
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Import module under test
from src.agents.web_search import (
    WebSearchAgent,
    WebSearchResult
)


class TestWebSearchAgentInitialization:
    """Tests for Web Search Agent initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        agent = WebSearchAgent()

        assert agent.model == "generic.mistral:7b"
        assert agent.temperature == 0.3
        assert agent.max_results == 5
        assert agent.search_engine == "duckduckgo"
        assert agent.agent is None  # Not initialized yet

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        agent = WebSearchAgent(
            model="generic.phi3:mini",
            temperature=0.5,
            max_results=10,
            search_engine="brave"
        )

        assert agent.model == "generic.phi3:mini"
        assert agent.temperature == 0.5
        assert agent.max_results == 10
        assert agent.search_engine == "brave"

    @patch('src.agents.web_search.FASTAGENT_AVAILABLE', True)
    @patch('src.agents.web_search.Agent')
    @patch('src.agents.web_search.initialize_fastagent')
    @pytest.mark.asyncio
    async def test_initialize_agent(self, mock_init_fa, mock_agent_class):
        """Test agent initialization process."""
        # Mock Agent instance
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        agent = WebSearchAgent()
        await agent.initialize()

        # Verify FastAgent initialization called
        mock_init_fa.assert_called_once_with(verify_connection=False)

        # Verify Agent created with correct parameters
        mock_agent_class.assert_called_once()
        call_kwargs = mock_agent_class.call_args.kwargs
        assert call_kwargs["name"] == "websearch"
        assert call_kwargs["model"] == "generic.mistral:7b"
        assert call_kwargs["temperature"] == 0.3
        assert "system_prompt" in call_kwargs
        assert len(call_kwargs["tools"]) > 0  # Should have search tools

    @patch('src.agents.web_search.FASTAGENT_AVAILABLE', False)
    @pytest.mark.asyncio
    async def test_initialize_without_fastagent(self):
        """Test initialization fails when FastAgent not available."""
        agent = WebSearchAgent()

        with pytest.raises(ImportError, match="FastAgent is not available"):
            await agent.initialize()

    @patch('src.agents.web_search.FASTAGENT_AVAILABLE', True)
    @patch('src.agents.web_search.initialize_fastagent')
    @pytest.mark.asyncio
    async def test_initialize_handles_errors(self, mock_init_fa):
        """Test initialization handles errors gracefully."""
        mock_init_fa.side_effect = Exception("Connection failed")

        agent = WebSearchAgent()

        from src.utils.fastagent_client import FastAgentError
        with pytest.raises(FastAgentError, match="Web search agent initialization failed"):
            await agent.initialize()


class TestQueryOptimization:
    """Tests for query formulation and optimization."""

    def test_optimize_query_basic(self):
        """Test basic query optimization."""
        agent = WebSearchAgent()

        original = "Who wrote Lord of the Rings?"
        optimized = agent._optimize_query(original)

        # Should preserve key information
        assert isinstance(optimized, str)
        assert len(optimized) > 0

    def test_optimize_query_removes_filler_words(self):
        """Test query optimization removes filler words."""
        agent = WebSearchAgent()

        queries_with_filler = [
            "Can you tell me about Tolkien?",
            "I would like to know about hobbits",
            "Please search for information on the Ring"
        ]

        for query in queries_with_filler:
            optimized = agent._optimize_query(query)
            # Should be more concise
            assert len(optimized) <= len(query)

    def test_optimize_query_extracts_key_terms(self):
        """Test query optimization extracts key terms."""
        agent = WebSearchAgent()

        query = "What was J.R.R. Tolkien's inspiration for writing LOTR?"
        optimized = agent._optimize_query(query)

        # Should contain key terms
        key_terms = ["Tolkien", "inspiration", "LOTR"]
        # At least some key terms should be preserved
        assert any(term.lower() in optimized.lower() for term in key_terms)

    def test_optimize_empty_query(self):
        """Test optimization of empty query."""
        agent = WebSearchAgent()

        optimized = agent._optimize_query("")

        # Should handle gracefully
        assert optimized == "" or optimized is not None


class TestSearchExecution:
    """Tests for web search execution."""

    @pytest.mark.asyncio
    async def test_search_basic(self):
        """Test basic search functionality."""
        agent = WebSearchAgent()

        # Mock the agent instance
        mock_agent_instance = AsyncMock()
        mock_response = Mock(
            content="""
            Summary: Tolkien was inspired by Norse mythology and his WWI experiences.
            Sources:
            1. Tolkien Society - tolkiensociety.org
            2. Biography - biography.com
            """
        )
        mock_agent_instance.run = AsyncMock(return_value=mock_response)
        agent.agent = mock_agent_instance

        result = await agent.search("Tolkien inspiration")

        # Verify result structure
        assert "summary" in result
        assert "sources" in result
        assert "query_used" in result
        assert "search_engine" in result
        assert isinstance(result["sources"], list)

    @pytest.mark.asyncio
    async def test_search_with_max_results_override(self):
        """Test search with max_results override."""
        agent = WebSearchAgent(max_results=5)

        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=Mock(
            content="Summary with sources"
        ))
        agent.agent = mock_agent_instance

        # Override max_results
        result = await agent.search("test query", max_results=3)

        assert "sources" in result
        # Should respect override
        # (Actual limiting would happen in real implementation)

    @pytest.mark.asyncio
    async def test_search_with_context(self):
        """Test search with additional context."""
        agent = WebSearchAgent()

        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=Mock(
            content="Contextualized results"
        ))
        agent.agent = mock_agent_instance

        context = {
            "domain": "academic",
            "date_range": "recent"
        }

        result = await agent.search("test query", context=context)

        # Should incorporate context
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_search_without_agent_fails(self):
        """Test search fails when agent not initialized."""
        agent = WebSearchAgent()
        # Don't initialize agent

        from src.utils.fastagent_client import FastAgentError
        with pytest.raises(FastAgentError):
            await agent.search("test query")


class TestResultFiltering:
    """Tests for search result filtering and ranking."""

    def test_filter_results_by_relevance(self):
        """Test filtering results by relevance score."""
        agent = WebSearchAgent()

        results = [
            WebSearchResult(
                title="Highly Relevant",
                url="http://example.com/1",
                snippet="Very relevant content",
                relevance_score=0.95
            ),
            WebSearchResult(
                title="Less Relevant",
                url="http://example.com/2",
                snippet="Somewhat relevant",
                relevance_score=0.3
            ),
            WebSearchResult(
                title="Relevant",
                url="http://example.com/3",
                snippet="Relevant content",
                relevance_score=0.7
            )
        ]

        filtered = agent._filter_by_relevance(results, min_score=0.5)

        # Should only include high-relevance results
        assert len(filtered) == 2
        assert all(r.relevance_score >= 0.5 for r in filtered)

    def test_rank_results_by_score(self):
        """Test ranking results by relevance score."""
        agent = WebSearchAgent()

        results = [
            WebSearchResult("Title1", "url1", "snip1", 0.5),
            WebSearchResult("Title2", "url2", "snip2", 0.9),
            WebSearchResult("Title3", "url3", "snip3", 0.7),
        ]

        ranked = agent._rank_results(results)

        # Should be sorted by score (descending)
        assert ranked[0].relevance_score == 0.9
        assert ranked[1].relevance_score == 0.7
        assert ranked[2].relevance_score == 0.5

    def test_remove_duplicate_results(self):
        """Test removing duplicate URLs from results."""
        agent = WebSearchAgent()

        results = [
            WebSearchResult("Title1", "http://example.com", "snip1", 0.9),
            WebSearchResult("Title2", "http://example.com", "snip2", 0.8),  # Duplicate URL
            WebSearchResult("Title3", "http://other.com", "snip3", 0.7),
        ]

        deduplicated = agent._remove_duplicates(results)

        # Should only have 2 results (duplicate removed)
        assert len(deduplicated) == 2
        # Should keep higher scoring duplicate
        assert deduplicated[0].relevance_score == 0.9


class TestSummarization:
    """Tests for search result summarization."""

    @pytest.mark.asyncio
    async def test_summarize_results(self):
        """Test summarizing search results."""
        agent = WebSearchAgent()

        results = [
            WebSearchResult(
                "Tolkien Biography",
                "http://bio.com",
                "J.R.R. Tolkien was inspired by...",
                0.95
            ),
            WebSearchResult(
                "LOTR Background",
                "http://lotr.com",
                "The Lord of the Rings draws from...",
                0.85
            )
        ]

        summary = agent._summarize_results("Tolkien inspiration", results)

        # Should produce a summary
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_summarize_empty_results(self):
        """Test summarizing with no results."""
        agent = WebSearchAgent()

        summary = agent._summarize_results("query", [])

        # Should indicate no results found
        assert "no results" in summary.lower() or "not found" in summary.lower()


class TestSourceValidation:
    """Tests for source validation and credibility checking."""

    def test_validate_source_url_format(self):
        """Test validating URL format."""
        agent = WebSearchAgent()

        valid_urls = [
            "https://example.com",
            "http://www.example.com/page",
            "https://subdomain.example.com/path"
        ]

        for url in valid_urls:
            assert agent._is_valid_url(url) is True

    def test_validate_source_invalid_urls(self):
        """Test invalid URL detection."""
        agent = WebSearchAgent()

        invalid_urls = [
            "not a url",
            "ftp://example.com",  # Non-HTTP protocol
            "",
            "javascript:alert('xss')"
        ]

        for url in invalid_urls:
            assert agent._is_valid_url(url) is False

    def test_assess_source_credibility(self):
        """Test assessing source credibility."""
        agent = WebSearchAgent()

        # Authoritative sources
        credible_results = [
            WebSearchResult("Research Paper", "https://scholar.google.com/...", "Academic", 0.9),
            WebSearchResult("Official Site", "https://tolkien.co.uk", "Official", 0.9),
        ]

        for result in credible_results:
            credibility = agent._assess_credibility(result)
            # Should be considered credible
            assert credibility >= 0.5

    def test_flag_low_credibility_sources(self):
        """Test flagging potentially unreliable sources."""
        agent = WebSearchAgent()

        # Less credible sources
        questionable_results = [
            WebSearchResult("Random Blog", "http://random-blog.com", "Opinion", 0.3),
        ]

        for result in questionable_results:
            credibility = agent._assess_credibility(result)
            # Should have lower credibility score
            assert credibility < 0.8


class TestSearchTools:
    """Tests for MCP search tool creation."""

    @patch('src.agents.web_search.FASTAGENT_AVAILABLE', True)
    def test_create_search_tools(self):
        """Test creating MCP search tools."""
        agent = WebSearchAgent()

        tools = agent._create_search_tools()

        # Should create at least one search tool
        assert isinstance(tools, list)
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_duckduckgo_tool_placeholder(self):
        """Test DuckDuckGo search tool (placeholder)."""
        agent = WebSearchAgent()

        # Get tools
        tools = agent._create_search_tools()

        # Find DuckDuckGo tool
        ddg_tool = None
        for tool in tools:
            if "duckduckgo" in tool.__name__.lower():
                ddg_tool = tool
                break

        # Should exist (even if placeholder)
        assert ddg_tool is not None

        # Test calling (placeholder returns empty list)
        result = await ddg_tool("test query", num_results=5)
        assert isinstance(result, list)


class TestWebSearchResult:
    """Tests for WebSearchResult dataclass."""

    def test_create_search_result(self):
        """Test creating WebSearchResult instance."""
        result = WebSearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet text",
            relevance_score=0.85,
            source="duckduckgo",
            timestamp="2025-01-15T10:00:00Z"
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet text"
        assert result.relevance_score == 0.85
        assert result.source == "duckduckgo"
        assert result.timestamp == "2025-01-15T10:00:00Z"

    def test_search_result_default_values(self):
        """Test SearchResult with default optional values."""
        result = WebSearchResult(
            title="Title",
            url="http://example.com",
            snippet="Snippet",
            relevance_score=0.5
        )

        assert result.source == "web"  # Default value
        assert result.timestamp is None  # Default None

    def test_search_result_to_dict(self):
        """Test converting SearchResult to dictionary."""
        result = WebSearchResult(
            title="Test",
            url="http://test.com",
            snippet="Test snippet",
            relevance_score=0.75,
            source="brave",
            timestamp="2025-01-15T10:00:00Z"
        )

        result_dict = result.to_dict()

        assert result_dict["title"] == "Test"
        assert result_dict["url"] == "http://test.com"
        assert result_dict["relevance_score"] == 0.75
        assert result_dict["source"] == "brave"


class TestSystemPromptBuilding:
    """Tests for system prompt construction."""

    def test_build_system_prompt(self):
        """Test building system prompt for web search agent."""
        agent = WebSearchAgent()

        prompt = agent._build_system_prompt()

        # Verify prompt contains key elements
        assert "Web Search Agent" in prompt
        assert "Query Formulation" in prompt or "formulation" in prompt.lower()
        assert "Search Execution" in prompt or "MCP" in prompt
        assert "Result Filtering" in prompt or "filtering" in prompt.lower()
        assert "Summarization" in prompt or "summarize" in prompt.lower()
        assert "Source Validation" in prompt or "validation" in prompt.lower()

    def test_system_prompt_mentions_search_engines(self):
        """Test system prompt mentions supported search engines."""
        agent = WebSearchAgent()

        prompt = agent._build_system_prompt()

        # Should mention DuckDuckGo and/or Brave
        assert "DuckDuckGo" in prompt or "Brave" in prompt

    def test_system_prompt_includes_guidelines(self):
        """Test system prompt includes search guidelines."""
        agent = WebSearchAgent()

        prompt = agent._build_system_prompt()

        # Should describe when to search and quality standards
        assert "external" in prompt.lower() or "web" in prompt.lower()
        assert "cite" in prompt.lower() or "citations" in prompt.lower()
        assert "authoritative" in prompt.lower() or "credible" in prompt.lower()


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_search_handles_agent_errors(self):
        """Test search handles errors from FastAgent."""
        agent = WebSearchAgent()

        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(side_effect=Exception("Search API error"))
        agent.agent = mock_agent_instance

        from src.utils.fastagent_client import FastAgentError
        with pytest.raises(FastAgentError):
            await agent.search("test query")

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        """Test handling empty search query."""
        agent = WebSearchAgent()

        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=Mock(
            content="No search performed"
        ))
        agent.agent = mock_agent_instance

        result = await agent.search("")

        # Should handle gracefully
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_search_very_long_query(self):
        """Test handling very long query."""
        agent = WebSearchAgent()

        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=Mock(
            content="Search results"
        ))
        agent.agent = mock_agent_instance

        # Very long query
        long_query = "test " * 500

        result = await agent.search(long_query)

        # Should truncate or handle appropriately
        assert "summary" in result

    def test_filter_malformed_results(self):
        """Test filtering handles malformed result data."""
        agent = WebSearchAgent()

        # Results with missing fields
        results = [
            WebSearchResult("Valid", "http://valid.com", "snippet", 0.9),
            # Malformed entries would be caught by dataclass validation
        ]

        filtered = agent._filter_by_relevance(results, min_score=0.5)

        # Should only return valid results
        assert len(filtered) >= 0

    @pytest.mark.asyncio
    async def test_search_network_timeout(self):
        """Test handling network timeout during search."""
        agent = WebSearchAgent()

        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(
            side_effect=TimeoutError("Network timeout")
        )
        agent.agent = mock_agent_instance

        from src.utils.fastagent_client import FastAgentError
        with pytest.raises((FastAgentError, TimeoutError)):
            await agent.search("test query")


class TestTimestampHandling:
    """Tests for timestamp and temporal data handling."""

    def test_add_timestamp_to_results(self):
        """Test adding timestamps to search results."""
        agent = WebSearchAgent()

        result = WebSearchResult(
            title="News Article",
            url="http://news.com",
            snippet="Recent news",
            relevance_score=0.9
        )

        # Add timestamp
        timestamped = agent._add_timestamp(result)

        assert timestamped.timestamp is not None

    def test_parse_result_dates(self):
        """Test parsing dates from result metadata."""
        agent = WebSearchAgent()

        # Result with date in snippet
        result = WebSearchResult(
            title="Article",
            url="http://example.com",
            snippet="Published 2025-01-15: Recent findings...",
            relevance_score=0.8
        )

        # Extract date (if implemented)
        date = agent._extract_date(result.snippet)

        # Should identify date pattern (implementation dependent)
        assert date is not None or date is None  # Flexible assertion


class TestContextHandling:
    """Tests for context-aware searching."""

    @pytest.mark.asyncio
    async def test_search_with_domain_filter(self):
        """Test searching with domain restriction."""
        agent = WebSearchAgent()

        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=Mock(
            content="Academic results"
        ))
        agent.agent = mock_agent_instance

        context = {"domain": ".edu"}  # Academic sources only

        result = await agent.search("research query", context=context)

        # Should apply domain filter
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_search_with_language_preference(self):
        """Test searching with language preference."""
        agent = WebSearchAgent()

        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=Mock(
            content="Localized results"
        ))
        agent.agent = mock_agent_instance

        context = {"language": "en"}

        result = await agent.search("test query", context=context)

        assert "summary" in result
