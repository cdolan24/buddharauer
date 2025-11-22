"""
Web Search Agent for external information retrieval.

This module implements the web search agent using FastAgent with MCP tools.
The agent handles queries that require external web search (current events,
general knowledge, information not in the document database).

The web search agent uses mistral:7b (fast and efficient for query generation
and result summarization) and integrates with MCP web search servers like
DuckDuckGo or Brave Search.

Architecture:
    Query → Query Formulation → Web Search (MCP) → Result Filtering → Summary

Key Features:
    - Query formulation and optimization
    - Web search via MCP tools (DuckDuckGo, Brave)
    - Result filtering and ranking
    - Summary generation with citations
    - Source validation

Usage:
    >>> from src.agents.web_search import WebSearchAgent
    >>> agent = WebSearchAgent()
    >>> await agent.initialize()
    >>> results = await agent.search("Latest news about AI")
    >>> print(results["summary"])
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

# FastAgent imports (conditional)
try:
    from fastagent import Agent
    from fastagent.core import tool
    FASTAGENT_AVAILABLE = True
except ImportError:
    FASTAGENT_AVAILABLE = False
    # Mock decorators for when FastAgent is not available
    def tool(func):
        return func
    Agent = None

from src.utils.fastagent_client import initialize_fastagent, FastAgentError

logger = logging.getLogger(__name__)


@dataclass
class WebSearchResult:
    """
    A web search result with metadata.

    Attributes:
        title: Page/result title
        url: Source URL
        snippet: Text snippet/description
        relevance_score: Relevance score (0.0-1.0)
        source: Search engine used
        timestamp: When the result was fetched
    """
    title: str
    url: str
    snippet: str
    relevance_score: float
    source: str = "web"
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class WebSearchAgent:
    """
    FastAgent-based web search agent for external information.

    The web search agent handles queries that require information outside
    the document database:
    1. Current events and news
    2. General knowledge questions
    3. Supplementary context
    4. Fact verification

    Uses mistral:7b for efficient query processing and result summarization.
    Integrates with MCP web search tools (DuckDuckGo, Brave Search, etc.).

    Attributes:
        agent: FastAgent Agent instance (if available)
        model: Model specification (default: generic.mistral:7b)
        temperature: Sampling temperature (default: 0.3)
        max_results: Maximum search results to process
        search_engine: Preferred search engine (duckduckgo, brave)

    Example:
        >>> web_search = WebSearchAgent()
        >>> await web_search.initialize()
        >>> result = await web_search.search(
        ...     query="What inspired Tolkien to write LOTR?",
        ...     max_results=5
        ... )
        >>> print(result["summary"])
        >>> for source in result["sources"]:
        ...     print(f"- {source['title']}: {source['url']}")
    """

    def __init__(
        self,
        model: str = "generic.mistral:7b",
        temperature: float = 0.3,
        max_results: int = 5,
        search_engine: str = "duckduckgo"
    ):
        """
        Initialize the web search agent.

        Args:
            model: FastAgent model specification for Ollama
                   mistral:7b recommended for speed and efficiency
            temperature: Sampling temperature (0.0-1.0)
                - Lower (0.2-0.4): More focused, factual
                - Higher (0.5-0.7): More creative summaries
            max_results: Maximum number of search results to return
            search_engine: Preferred search engine (duckduckgo, brave, etc.)

        Raises:
            FastAgentError: If FastAgent initialization fails
        """
        self.model = model
        self.temperature = temperature
        self.max_results = max_results
        self.search_engine = search_engine
        self.agent = None

        logger.info(
            f"WebSearchAgent initialized with model={model}, "
            f"search_engine={search_engine}"
        )

    async def initialize(self) -> None:
        """
        Initialize the FastAgent web search agent.

        Sets up the FastAgent instance with Ollama configuration and
        MCP web search tools.

        Raises:
            FastAgentError: If FastAgent initialization fails
            ImportError: If fastagent package is not installed
        """
        if not FASTAGENT_AVAILABLE:
            raise ImportError(
                "FastAgent is not available. Install with: pip install fast-agent-mcp"
            )

        try:
            # Initialize FastAgent with Ollama configuration
            initialize_fastagent(verify_connection=False)  # Non-blocking initialization
            logger.info("FastAgent initialized with Ollama connection")

            # Create system prompt for web search
            system_prompt = self._build_system_prompt()

            # Create the FastAgent Agent instance with web search tools
            # MCP tools for web search will be added via _create_search_tools()
            tools = self._create_search_tools()

            self.agent = Agent(
                name="websearch",
                model=self.model,
                system_prompt=system_prompt,
                temperature=self.temperature,
                tools=tools
            )

            logger.info(f"WebSearchAgent FastAgent instance created with {len(tools)} tools")

        except Exception as e:
            logger.error(f"Failed to initialize WebSearchAgent: {e}")
            raise FastAgentError(f"Web search agent initialization failed: {e}")

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the web search agent.

        Returns:
            System prompt string for FastAgent
        """
        return """You are the Web Search Agent for Buddharauer, specializing in external information retrieval.

Your role is to search the web when document database information is insufficient:

1. **Query Formulation**: Optimize user queries for web search
   - Extract key terms and concepts
   - Add context for better results
   - Remove irrelevant words

2. **Search Execution**: Use MCP web search tools
   - DuckDuckGo for general searches (no API key needed)
   - Brave Search for comprehensive results
   - Handle search errors gracefully

3. **Result Filtering**: Select most relevant results
   - Filter by relevance and quality
   - Verify source credibility
   - Remove duplicate or low-quality results

4. **Summarization**: Create coherent summaries
   - Synthesize information from multiple sources
   - Maintain factual accuracy
   - Cite sources with URLs

5. **Source Validation**: Ensure quality
   - Prefer authoritative sources
   - Note publication dates for time-sensitive info
   - Flag potentially unreliable sources

Guidelines:
- Only search when external information is needed
- Prioritize recent, authoritative sources
- Provide clear citations with URLs
- Acknowledge when information is not found
- Be concise but informative

Output Format:
- Summary: Clear overview of findings
- Sources: List of URLs with titles and snippets
- Note any limitations or uncertainties"""

    def _create_search_tools(self) -> List:
        """
        Create MCP tools for web search functionality.

        Returns:
            List of tool functions for FastAgent

        Note:
            This creates placeholder tools for web search. In production,
            these should be replaced with actual MCP web search server tools
            (e.g., DuckDuckGo MCP, Brave Search MCP).
        """
        tools = []

        @tool
        async def search_duckduckgo(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
            """
            Search DuckDuckGo for web results.

            Args:
                query: Search query
                num_results: Number of results to return

            Returns:
                List of search result dictionaries
            """
            # Placeholder implementation - replace with actual MCP tool call
            # In production, this would use the DuckDuckGo MCP server
            logger.info(f"DuckDuckGo search: {query} (placeholder)")
            return []

        tools.append(search_duckduckgo)
        return tools

    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform web search and return results.

        This is the main entry point for web search tasks. The agent:
        1. Formulates an optimized search query
        2. Executes search via MCP tools
        3. Filters and ranks results
        4. Generates summary with citations

        Args:
            query: Search query
            max_results: Optional override for max results
            context: Optional context (filters, preferences, etc.)

        Returns:
            Search result dict containing:
                - summary: Summarized findings
                - sources: List of WebSearchResult dicts
                - query_used: Actual search query used
                - search_engine: Search engine used
                - timestamp: When search was performed

        Raises:
            FastAgentError: If search fails

        Example:
            >>> result = await web_search.search(
            ...     query="Tolkien's inspiration for Middle Earth",
            ...     max_results=5
            ... )
            >>> print(result["summary"])
            >>> for source in result["sources"]:
            ...     print(f"{source['title']}: {source['url']}")
        """
        try:
            # Use provided max_results or default
            limit = max_results or self.max_results

            logger.info(f"Web search: {query[:50]}... (limit={limit})")

            # Formulate optimized search query
            optimized_query = self._optimize_query(query)
            logger.info(f"Optimized query: {optimized_query}")

            # Execute search via helper method
            # The FastAgent agent will use the search_duckduckgo tool defined in _create_search_tools()
            raw_results = await self._execute_search(optimized_query, limit)

            # Filter and rank results
            filtered_results = self._filter_results(raw_results, limit)

            # Generate summary
            summary = self._generate_summary(query, filtered_results)

            # Format response
            response = {
                "summary": summary,
                "sources": [r.to_dict() for r in filtered_results],
                "query_used": optimized_query,
                "search_engine": self.search_engine,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result_count": len(filtered_results)
            }

            logger.info(f"Web search completed: {len(filtered_results)} results")
            return response

        except Exception as e:
            logger.error(f"Web search failed: {e}", exc_info=True)
            raise FastAgentError(f"Failed to perform web search: {e}")

    def _optimize_query(self, query: str) -> str:
        """
        Optimize the user query for web search.

        Simple optimization for now. In production, use LLM for query expansion.

        Args:
            query: Original user query

        Returns:
            Optimized search query
        """
        # Remove question words that don't help search
        query_lower = query.lower()
        remove_words = ["tell me about", "what is", "who is", "where is", "explain"]

        optimized = query
        for word in remove_words:
            optimized = optimized.lower().replace(word, "")

        # Clean up extra spaces
        optimized = " ".join(optimized.split())

        # If query is too short, return original
        if len(optimized) < 3:
            return query

        return optimized.strip()

    async def _execute_search(
        self,
        query: str,
        limit: int
    ) -> List[WebSearchResult]:
        """
        Execute web search via MCP tools.

        This is a placeholder that will be replaced with actual MCP tool calls.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of WebSearchResult objects

        Raises:
            Exception: If the agent fails to execute search
        """
        # If agent is available, use it (for testing or actual MCP integration)
        if self.agent:
            try:
                # Call the agent with search query
                # In production, this would trigger the MCP tools
                response = await self.agent.run(f"Search for: {query}")
                # Parse response and return results
                # For now, this is mainly for test compatibility
                logger.info("Agent search executed")
            except Exception as e:
                # Re-raise for proper error handling in search()
                logger.error(f"Agent search failed: {e}")
                raise

        # Placeholder implementation until MCP web search server is configured
        # To enable actual web search:
        # 1. Install MCP web search server (e.g., duckduckgo-mcp or brave-search-mcp)
        # 2. Update _create_search_tools() to use the MCP tool
        # 3. Configure MCP server in fastagent.config.yaml

        logger.warning("MCP web search not yet implemented - returning placeholder")

        # Placeholder results
        placeholder_results = [
            WebSearchResult(
                title=f"Search result for: {query}",
                url="https://example.com/placeholder",
                snippet="Web search functionality requires MCP tools integration. "
                        "Install and configure DuckDuckGo or Brave Search MCP server.",
                relevance_score=0.5,
                source=self.search_engine,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        ]

        return placeholder_results

    def _filter_results(
        self,
        results: List[WebSearchResult],
        limit: int
    ) -> List[WebSearchResult]:
        """
        Filter and rank search results.

        Args:
            results: Raw search results
            limit: Maximum results to return

        Returns:
            Filtered and ranked results
        """
        if not results:
            return []

        # Sort by relevance score (descending)
        sorted_results = sorted(
            results,
            key=lambda r: r.relevance_score,
            reverse=True
        )

        # Take top N results
        return sorted_results[:limit]

    def _generate_summary(
        self,
        query: str,
        results: List[WebSearchResult]
    ) -> str:
        """
        Generate summary from search results.

        Args:
            query: Original query
            results: Filtered search results

        Returns:
            Summary text
        """
        if not results:
            return "No web search results found. Please try a different query or search the document database."

        # Build summary from top results
        summary_parts = [f"Web search results for: {query}\n"]

        for i, result in enumerate(results[:3], 1):  # Top 3 results
            summary_parts.append(
                f"{i}. {result.title}\n   {result.snippet}\n   Source: {result.url}\n"
            )

        if len(results) > 3:
            summary_parts.append(
                f"\n...and {len(results) - 3} more result(s). "
                "See sources for complete list."
            )

        return "\n".join(summary_parts)

    async def verify_fact(
        self,
        statement: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a factual statement using web search.

        Args:
            statement: Statement to verify
            context: Optional context

        Returns:
            Verification result with sources
        """
        try:
            # Formulate verification query
            verification_query = f"verify: {statement}"
            if context:
                verification_query += f" context: {context}"

            # Execute search
            results = await self.search(verification_query, max_results=3)

            # Analyze results for verification
            # Future enhancement: Use the FastAgent agent to analyze search results
            # and determine if the statement is supported by the sources

            return {
                "statement": statement,
                "verified": None,  # True/False/None (unknown)
                "confidence": 0.0,
                "sources": results.get("sources", []),
                "note": "Fact verification requires full MCP integration"
            }

        except Exception as e:
            logger.error(f"Fact verification failed: {e}")
            return {
                "statement": statement,
                "verified": None,
                "confidence": 0.0,
                "sources": [],
                "error": str(e)
            }

    def is_web_search_needed(self, query: str) -> bool:
        """
        Determine if a query requires web search.

        Simple heuristic to check if query needs external info.

        Args:
            query: User query

        Returns:
            True if web search is likely needed
        """
        query_lower = query.lower()

        # Keywords indicating web search need
        web_indicators = [
            "latest", "recent", "current", "today", "news",
            "what is happening", "updates on", "now",
            "google", "search", "look up", "find online",
            "real world", "actual", "in reality"
        ]

        return any(indicator in query_lower for indicator in web_indicators)

    # ========== Helper Methods for Result Processing ==========
    # These methods are used to filter, validate, and process search results

    def _filter_by_relevance(
        self,
        results: List[WebSearchResult],
        min_score: float = 0.3
    ) -> List[WebSearchResult]:
        """
        Filter results by minimum relevance score.

        Args:
            results: List of search results
            min_score: Minimum relevance score threshold (0.0-1.0)

        Returns:
            Filtered list of results meeting the threshold
        """
        return [r for r in results if r.relevance_score >= min_score]

    def _rank_results(
        self,
        results: List[WebSearchResult]
    ) -> List[WebSearchResult]:
        """
        Rank results by relevance score in descending order.

        Args:
            results: List of search results to rank

        Returns:
            Sorted list of results (highest relevance first)
        """
        return sorted(
            results,
            key=lambda r: r.relevance_score,
            reverse=True
        )

    def _remove_duplicates(
        self,
        results: List[WebSearchResult]
    ) -> List[WebSearchResult]:
        """
        Remove duplicate results based on URL.

        Args:
            results: List of search results

        Returns:
            Deduplicated list of results
        """
        seen_urls = set()
        unique_results = []

        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)

        return unique_results

    def _summarize_results(
        self,
        query: str,
        results: List[WebSearchResult],
        max_length: int = 500
    ) -> str:
        """
        Create a concise summary from search results.

        Args:
            query: Original search query
            results: List of search results
            max_length: Maximum summary length in characters

        Returns:
            Summarized text from top results
        """
        if not results:
            return "No results found."

        # Combine snippets from top results
        snippets = [r.snippet for r in results[:3]]
        combined = " ".join(snippets)

        # Truncate if too long
        if len(combined) > max_length:
            combined = combined[:max_length - 3] + "..."

        return combined

    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format.

        Args:
            url: URL string to validate

        Returns:
            True if URL has valid format
        """
        import re

        # Basic URL pattern validation
        # Checks for http(s):// followed by domain
        url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

        return bool(re.match(url_pattern, url))

    def _assess_credibility(
        self,
        result: WebSearchResult
    ) -> float:
        """
        Assess source credibility based on URL and metadata.

        This is a simple heuristic-based assessment. In production,
        this could be enhanced with:
        - Domain reputation databases
        - Content analysis
        - Cross-referencing with known authoritative sources

        Args:
            result: Search result to assess

        Returns:
            Credibility score (0.0-1.0)
                - 0.0-0.4: Low credibility
                - 0.4-0.7: Medium credibility
                - 0.7-1.0: High credibility
        """
        url_lower = result.url.lower()
        score = 0.5  # Default neutral score

        # Known high-credibility domain patterns
        high_credibility_domains = [
            '.edu', '.gov', '.org',
            'wikipedia.org', 'britannica.com',
            'arxiv.org', 'scholar.google'
        ]

        # Known low-credibility patterns
        low_credibility_patterns = [
            'blogspot', 'wordpress.com', 'medium.com',
            'pinterest', 'reddit.com'
        ]

        # Check for high credibility indicators
        for domain in high_credibility_domains:
            if domain in url_lower:
                score += 0.3
                break

        # Check for low credibility indicators
        for pattern in low_credibility_patterns:
            if pattern in url_lower:
                score -= 0.2
                break

        # Check for HTTPS (secure connection)
        if result.url.startswith('https://'):
            score += 0.1

        # Normalize score to 0.0-1.0 range
        score = max(0.0, min(1.0, score))

        return round(score, 2)

    def _add_timestamp(
        self,
        results
    ):
        """
        Add current timestamp to results that don't have one.

        Args:
            results: Single WebSearchResult or list of results

        Returns:
            Result(s) with timestamps added (same type as input)
        """
        from typing import Union

        current_time = datetime.now(timezone.utc).isoformat()

        # Handle single result
        if isinstance(results, WebSearchResult):
            if not results.timestamp:
                results.timestamp = current_time
            return results

        # Handle list of results
        for result in results:
            if not result.timestamp:
                result.timestamp = current_time

        return results

    def _extract_date(
        self,
        text: str
    ) -> Optional[str]:
        """
        Extract publication date from result text.

        This is a simple pattern-based extraction. In production,
        this could use more sophisticated NLP or metadata extraction.

        Args:
            text: Text to extract date from

        Returns:
            Extracted date string if found, None otherwise
        """
        import re

        # Common date patterns
        # Format: YYYY-MM-DD, MM/DD/YYYY, Month DD, YYYY
        patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',  # Month DD, YYYY
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)

        return None
