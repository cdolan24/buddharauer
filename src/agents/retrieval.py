"""
Retrieval Agent for document search and RAG.

This module implements the retrieval agent using FastAgent. The agent specializes
in semantic search over the vector database, query reformulation, and re-ranking
results for optimal relevance.

The retrieval agent uses qwen2.5:latest model (officially tested by FastAgent for
tool calling) and provides MCP tools for vector store access.

Architecture:
    Query → Query Reformulation → Vector Search → Re-ranking → Results

Key Features:
    - Semantic search using Ollama embeddings (nomic-embed-text)
    - Query reformulation for better retrieval
    - Result re-ranking by relevance
    - Source citation with metadata
    - Integration with VectorStore

Usage:
    >>> from src.agents.retrieval import RetrievalAgent
    >>> agent = RetrievalAgent()
    >>> results = await agent.search("Who is Aragorn?")
    >>> for result in results:
    ...     print(f"{result['text']} (score: {result['score']:.2f})")
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

# VectorStore import
from src.database.vector_store import VectorStore
from src.database.document_registry import DocumentRegistry

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
class SearchResult:
    """A search result with metadata."""
    chunk_id: str
    document_id: str
    text: str
    score: float
    page: Optional[int] = None
    document_title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RetrievalAgent:
    """
    FastAgent-based retrieval agent for semantic document search.

    The retrieval agent handles:
    1. Query understanding and reformulation
    2. Semantic search via vector database
    3. Result re-ranking and filtering
    4. Source citation enrichment

    Uses qwen2.5:latest model for better tool calling performance.

    Attributes:
        vector_store: VectorStore instance for semantic search
        document_registry: DocumentRegistry for document metadata
        agent: FastAgent Agent instance (if available)
        model: Model specification (default: generic.qwen2.5:latest)
        temperature: Sampling temperature (default: 0.5)

    Example:
        >>> agent = RetrievalAgent()
        >>> await agent.initialize()
        >>> results = await agent.search("Tell me about Gandalf", limit=5)
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        document_registry: Optional[DocumentRegistry] = None,
        model: str = "generic.qwen2.5:latest",
        temperature: float = 0.5
    ):
        """
        Initialize the retrieval agent.

        Args:
            vector_store: VectorStore instance. If None, creates new instance.
            document_registry: DocumentRegistry instance. If None, creates new.
            model: FastAgent model specification (default: qwen2.5:latest)
            temperature: Sampling temperature 0.0-1.0 (default: 0.5)

        Raises:
            FastAgentError: If FastAgent is not available
        """
        if not FASTAGENT_AVAILABLE:
            logger.warning("FastAgent not available - agent functionality limited")

        self.vector_store = vector_store or VectorStore()
        self.document_registry = document_registry or DocumentRegistry()
        self.model = model
        self.temperature = temperature
        self.agent: Optional[Agent] = None

        logger.info(f"RetrievalAgent initialized with model {model}")

    async def initialize(self) -> bool:
        """
        Initialize FastAgent and create the agent.

        Must be called before using the agent for searches.

        Returns:
            True if initialization successful, False otherwise

        Raises:
            FastAgentError: If FastAgent initialization fails

        Example:
            >>> agent = RetrievalAgent()
            >>> success = await agent.initialize()
            >>> if success:
            ...     results = await agent.search("query")
        """
        if not FASTAGENT_AVAILABLE:
            logger.error("Cannot initialize: FastAgent not installed")
            return False

        try:
            # Initialize FastAgent environment
            initialize_fastagent(verify_connection=True)

            # System prompt for retrieval agent
            system_prompt = """You are a specialized document retrieval agent with access to a vector database of PDF documents.

Your role is to:
1. Understand user search queries and reformulate them for better semantic search
2. Search the vector database for relevant document chunks
3. Re-rank results by relevance and context
4. Return the most pertinent passages with complete metadata

Always preserve document metadata (title, page number, chunk ID) in your results.
Prioritize precision over recall - return highly relevant results rather than many loosely related ones.

When reformulating queries:
- Extract key entities and concepts
- Expand acronyms and abbreviations
- Consider synonyms and related terms
- Focus on searchable content rather than questions"""

            # Create the agent (tools will be registered via MCP)
            self.agent = Agent(
                name="retrieval",
                model=self.model,
                system_prompt=system_prompt,
                temperature=self.temperature,
                tools=[]  # Tools added via self._create_tools()
            )

            logger.info("Retrieval agent initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize retrieval agent: {e}")
            raise FastAgentError(f"Retrieval agent initialization failed: {e}")

    async def search(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        Search for relevant document chunks.

        Performs semantic search over the vector database and returns
        ranked results with metadata enrichment.

        Args:
            query: User's search query
            limit: Maximum number of results (default: 5)
            filters: Optional metadata filters (e.g., {"document_id": "doc_001"})
            min_score: Minimum relevance score threshold (default: 0.0)

        Returns:
            List of SearchResult objects sorted by relevance score

        Raises:
            FastAgentError: If search fails or agent not initialized

        Example:
            >>> results = await agent.search("Who is Aragorn?", limit=3)
            >>> for result in results:
            ...     print(f"Page {result.page}: {result.text[:100]}")
        """
        try:
            # Perform vector search
            search_results = await self.vector_store.search(
                query_texts=[query],
                n_results=limit,
                where=filters
            )

            # Convert to SearchResult objects and enrich with metadata
            results = []
            for result in search_results:
                # Extract chunk metadata
                chunk_id = result.get("id", "unknown")
                text = result.get("text", "")
                score = result.get("score", 0.0)
                metadata = result.get("metadata", {})

                # Filter by minimum score
                if score < min_score:
                    continue

                # Extract document info from metadata
                document_id = metadata.get("document_id", "unknown")
                page = metadata.get("page")

                # Enrich with document registry data
                document_title = "unknown"
                try:
                    doc_record = await self.document_registry.get_by_id(document_id)
                    if doc_record:
                        document_title = doc_record.filename
                except Exception as e:
                    logger.warning(f"Could not fetch document title for {document_id}: {e}")

                # Create search result
                search_result = SearchResult(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    text=text,
                    score=score,
                    page=page,
                    document_title=document_title,
                    metadata=metadata
                )
                results.append(search_result)

            logger.info(f"Search returned {len(results)} results for query: {query[:50]}...")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise FastAgentError(f"Search operation failed: {e}")

    async def reformulate_query(self, query: str) -> str:
        """
        Reformulate user query for better semantic search.

        Uses the FastAgent agent to understand the query and reformulate it
        into a more effective search query with key terms and concepts.

        Args:
            query: Original user query

        Returns:
            Reformulated query optimized for semantic search

        Example:
            >>> original = "Who's the ranger guy in LOTR?"
            >>> reformulated = await agent.reformulate_query(original)
            >>> print(reformulated)
            "Aragorn ranger Middle-earth Lord of the Rings Strider"
        """
        if not self.agent:
            logger.warning("Agent not initialized, returning original query")
            return query

        try:
            # Use FastAgent to reformulate query
            # This is a placeholder - actual implementation would use agent.run()
            # with a specific prompt for query reformulation
            logger.info(f"Query reformulation requested: {query}")
            # For now, return original query until FastAgent integration complete
            return query

        except Exception as e:
            logger.error(f"Query reformulation failed: {e}")
            # Fall back to original query
            return query

    async def rerank_results(
        self,
        query: str,
        results: List[SearchResult],
        limit: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Re-rank search results using contextual understanding.

        Uses the FastAgent agent to re-score and re-order results based on
        deeper understanding of the query intent and content relevance.

        Args:
            query: Original search query
            results: Initial search results to re-rank
            limit: Optional limit on number of results to return

        Returns:
            Re-ranked list of SearchResult objects

        Example:
            >>> initial_results = await agent.search("Gandalf", limit=10)
            >>> reranked = await agent.rerank_results("Gandalf", initial_results, limit=5)
        """
        # Handle empty results
        if not results:
            return results

        try:
            # Even without FastAgent, we should sort by score (basic re-ranking)
            # When FastAgent is available, this would use LLM-based re-scoring
            if self.agent:
                logger.info(f"Re-ranking {len(results)} results for query: {query[:50]}...")
                # Placeholder for FastAgent-based re-ranking
                # Actual implementation would use agent to score and reorder

            # Sort results by score (descending)
            sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
            return sorted_results[:limit] if limit else sorted_results

        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            # Fall back to score-based sorting
            sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
            return sorted_results[:limit] if limit else sorted_results

    def to_dict(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """
        Convert search results to dictionary format.

        Useful for API responses and serialization.

        Args:
            results: List of SearchResult objects

        Returns:
            List of dictionaries with result data

        Example:
            >>> results = await agent.search("query")
            >>> dict_results = agent.to_dict(results)
            >>> import json
            >>> json.dumps(dict_results)
        """
        return [asdict(result) for result in results]


# MCP Tool Functions for Vector Store Access
# These will be registered with the FastAgent agent

@tool
async def vector_search_tool(
    query: str,
    limit: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    MCP tool for vector database search.

    This tool is exposed to the FastAgent agent for semantic search
    over the vector database.

    Args:
        query: Search query text
        limit: Maximum results to return
        filters: Optional metadata filters

    Returns:
        List of search results with metadata

    Example:
        (This tool is used by the FastAgent agent, not called directly)
        Agent prompt: "Search for information about Aragorn"
        → Tool call: vector_search_tool(query="Aragorn ranger", limit=5)
    """
    # Create temporary vector store instance
    # In production, this would use dependency injection
    vector_store = VectorStore()

    try:
        results = await vector_store.search(
            query_texts=[query],
            n_results=limit,
            where=filters
        )
        # ChromaDB returns dict with 'ids', 'documents', 'metadatas', 'distances'
        # Convert to list of dicts for MCP tool compatibility
        if isinstance(results, dict) and 'ids' in results:
            # Format ChromaDB results as list of dicts
            formatted_results = []
            if results.get('ids') and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i] if results['ids'][0] else None,
                        'text': results['documents'][0][i] if results.get('documents') and results['documents'][0] else '',
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') and results['metadatas'][0] else {},
                        'distance': results['distances'][0][i] if results.get('distances') and results['distances'][0] else 0
                    })
            return formatted_results
        return results if isinstance(results, list) else []
    except Exception as e:
        logger.error(f"Vector search tool failed: {e}")
        return []


# Factory function for easy agent creation

async def create_retrieval_agent(
    vector_store: Optional[VectorStore] = None,
    document_registry: Optional[DocumentRegistry] = None
) -> RetrievalAgent:
    """
    Create and initialize a retrieval agent.

    Convenience factory function that creates the agent and initializes
    FastAgent in one step.

    Args:
        vector_store: Optional VectorStore instance
        document_registry: Optional DocumentRegistry instance

    Returns:
        Initialized RetrievalAgent ready for use

    Raises:
        FastAgentError: If initialization fails

    Example:
        >>> agent = await create_retrieval_agent()
        >>> results = await agent.search("Who is Gandalf?")
    """
    agent = RetrievalAgent(
        vector_store=vector_store,
        document_registry=document_registry
    )
    await agent.initialize()
    return agent
