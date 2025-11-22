"""
Orchestrator Agent - Main coordination agent for Buddharauer.

This module implements the orchestrator agent using FastAgent. The orchestrator
is the main user-facing agent that routes requests to specialized sub-agents
(Analyst, Retrieval, WebSearch) and manages conversation flow.

The orchestrator uses llama3.2:latest model (officially tested by FastAgent for
multi-agent coordination and tool calling) and provides the primary interface
between the FastAPI backend and the agent ecosystem.

Architecture:
    User Query → Orchestrator → [Analyst | Retrieval | WebSearch] → Response

Key Features:
    - Intent classification and routing
    - Multi-turn conversation management
    - Sub-agent coordination via MCP tools
    - Response formatting with citations
    - Context window management

Usage:
    >>> from src.agents.orchestrator import OrchestratorAgent
    >>> orchestrator = OrchestratorAgent()
    >>> await orchestrator.initialize()
    >>> response = await orchestrator.process("Who is Gandalf?")
    >>> print(response["content"])
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

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


class IntentType(Enum):
    """User intent classification for routing."""
    QUESTION = "question"           # Factual question requiring retrieval
    SUMMARY = "summary"              # Request for summary or analysis
    EXPLORATION = "exploration"      # Open-ended exploration
    WEB_SEARCH = "web_search"       # Requires external web search
    CLARIFICATION = "clarification" # Need more context from user
    UNKNOWN = "unknown"             # Unable to determine intent


@dataclass
class OrchestratorResponse:
    """
    Response from the orchestrator agent.

    Attributes:
        content: The main response text
        intent: Classified user intent
        agent_used: Which sub-agent(s) were invoked
        sources: List of source citations
        conversation_id: ID for conversation tracking
        metadata: Additional response metadata
    """
    content: str
    intent: IntentType
    agent_used: List[str]
    sources: List[Dict[str, Any]]
    conversation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "content": self.content,
            "intent": self.intent.value if isinstance(self.intent, IntentType) else self.intent,
            "agent_used": self.agent_used,
            "sources": self.sources,
            "conversation_id": self.conversation_id,
            "metadata": self.metadata or {}
        }


class OrchestratorAgent:
    """
    FastAgent-based orchestrator for multi-agent coordination.

    The orchestrator agent is the primary entry point for all user interactions.
    It classifies user intent, routes to appropriate sub-agents, and formats
    responses for the frontend.

    Responsibilities:
        1. Parse and understand user messages
        2. Classify intent (question, summary, web search, etc.)
        3. Route to appropriate sub-agents via MCP tools
        4. Combine and format responses
        5. Maintain conversation context
        6. Generate citations and source references

    The orchestrator uses llama3.2:latest for robust reasoning and tool calling.

    Attributes:
        agent: FastAgent Agent instance (if available)
        model: Model specification (default: generic.llama3.2:latest)
        temperature: Sampling temperature (default: 0.7)
        conversation_history: Dict mapping conversation IDs to message history
        max_context_length: Maximum tokens in context window

    Example:
        >>> orchestrator = OrchestratorAgent()
        >>> await orchestrator.initialize()
        >>> response = await orchestrator.process(
        ...     message="What is the Ring of Power?",
        ...     conversation_id="conv_123"
        ... )
        >>> print(f"Response: {response['content']}")
        >>> print(f"Sources: {len(response['sources'])}")
    """

    def __init__(
        self,
        model: str = "generic.llama3.2:latest",
        temperature: float = 0.7,
        max_context_length: int = 4096
    ):
        """
        Initialize the orchestrator agent.

        Args:
            model: FastAgent model specification for Ollama
            temperature: Sampling temperature (0.0-1.0)
                - Lower (0.3-0.5): More focused, deterministic
                - Higher (0.7-1.0): More creative, varied
            max_context_length: Maximum tokens in context window

        Raises:
            FastAgentError: If FastAgent initialization fails
        """
        self.model = model
        self.temperature = temperature
        self.max_context_length = max_context_length
        self.max_history_length = 50  # Max messages to keep per conversation
        self.agent = None
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}

        # Sub-agent references (will be injected during initialization)
        self.retrieval_agent = None
        self.analyst_agent = None
        self.web_search_agent = None

        logger.info(
            f"OrchestratorAgent initialized with model={model}, "
            f"temperature={temperature}"
        )

    async def initialize(
        self,
        retrieval_agent=None,
        analyst_agent=None,
        web_search_agent=None
    ) -> None:
        """
        Initialize the FastAgent orchestrator and register sub-agents.

        This method sets up the FastAgent instance with the Ollama configuration
        and registers MCP tools for calling sub-agents.

        Args:
            retrieval_agent: RetrievalAgent instance for document search
            analyst_agent: AnalystAgent instance for analysis tasks
            web_search_agent: WebSearchAgent instance for external search

        Raises:
            FastAgentError: If FastAgent initialization fails
            ImportError: If fastagent package is not installed
        """
        if not FASTAGENT_AVAILABLE:
            raise ImportError(
                "FastAgent is not available. Install with: pip install fast-agent-mcp"
            )

        try:
            # Store sub-agent references
            self.retrieval_agent = retrieval_agent
            self.analyst_agent = analyst_agent
            self.web_search_agent = web_search_agent

            # Initialize FastAgent with Ollama configuration
            # The initialize_fastagent function sets up GENERIC_API_KEY and GENERIC_BASE_URL
            initialize_fastagent(verify_connection=False)  # Non-blocking initialization
            logger.info("FastAgent initialized with Ollama connection")

            # Create FastAgent instance with system prompt for orchestration
            system_prompt = self._build_system_prompt()

            # Create the FastAgent Agent instance with tools for sub-agents
            # Tools will be methods that the Agent can call to invoke sub-agents
            tools = []
            if self.retrieval_agent:
                tools.append(self._create_retrieval_tool())
            if self.analyst_agent:
                tools.append(self._create_analyst_tool())
            if self.web_search_agent:
                tools.append(self._create_websearch_tool())

            # Initialize the FastAgent Agent
            self.agent = Agent(
                name="orchestrator",
                model=self.model,
                system_prompt=system_prompt,
                temperature=self.temperature,
                tools=tools
            )

            logger.info(f"OrchestratorAgent FastAgent instance created with {len(tools)} tools")

        except Exception as e:
            logger.error(f"Failed to initialize OrchestratorAgent: {e}")
            raise FastAgentError(f"Orchestrator initialization failed: {e}")

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the orchestrator agent.

        The system prompt defines the orchestrator's role, capabilities,
        and routing logic.

        Returns:
            System prompt string for FastAgent
        """
        return """You are the Orchestrator Agent for Buddharauer, an AI-powered document analysis system.

Your role is to understand user questions and route them to specialized sub-agents:

1. **Retrieval Agent**: Use for factual questions about documents in the database
   - Example: "Who is Aragorn?" → Use retrieval to search documents

2. **Analyst Agent**: Use for summaries, analysis, and creative insights
   - Example: "Summarize all references to the Ring" → Use analyst

3. **Web Search Agent**: Use when external information is needed
   - Example: "What was Tolkien's inspiration for LOTR?" → Use web search

4. **Multiple Agents**: You can invoke multiple agents if needed
   - Example: "Compare book Aragorn to movie Aragorn" → Use retrieval + web search

Guidelines:
- Always provide clear, well-formatted responses
- Include source citations with page numbers when available
- If uncertain, ask the user for clarification
- Maintain conversation context across multiple turns
- Be concise but informative

Your responses should be helpful, accurate, and cite sources appropriately."""

    def _create_retrieval_tool(self):
        """
        Create a FastAgent tool for invoking the retrieval agent.

        Returns:
            Tool function decorated with @tool for FastAgent
        """
        @tool
        async def search_documents(query: str, limit: int = 5) -> Dict[str, Any]:
            """
            Search the document database for relevant information.

            Args:
                query: The search query
                limit: Maximum number of results to return

            Returns:
                Dictionary with search results and metadata
            """
            if not self.retrieval_agent:
                return {
                    "error": "Retrieval agent not available",
                    "results": []
                }

            try:
                # Call the retrieval agent's search method
                results = await self.retrieval_agent.search(
                    query=query,
                    limit=limit
                )
                return results
            except Exception as e:
                logger.error(f"Retrieval tool error: {e}")
                return {
                    "error": str(e),
                    "results": []
                }

        return search_documents

    def _create_analyst_tool(self):
        """
        Create a FastAgent tool for invoking the analyst agent.

        Returns:
            Tool function decorated with @tool for FastAgent
        """
        @tool
        async def analyze_content(
            query: str,
            analysis_type: str = "summary",
            content: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Analyze content or generate insights.

            Args:
                query: The analysis query/task
                analysis_type: Type of analysis (summary, character, theme, etc.)
                content: Optional content to analyze directly

            Returns:
                Dictionary with analysis results
            """
            if not self.analyst_agent:
                return {
                    "error": "Analyst agent not available",
                    "analysis": {}
                }

            try:
                # Call the analyst agent's analyze method
                results = await self.analyst_agent.analyze(
                    query=query,
                    analysis_type=analysis_type,
                    content=content
                )
                return results
            except Exception as e:
                logger.error(f"Analyst tool error: {e}")
                return {
                    "error": str(e),
                    "analysis": {}
                }

        return analyze_content

    def _create_websearch_tool(self):
        """
        Create a FastAgent tool for invoking the web search agent.

        Returns:
            Tool function decorated with @tool for FastAgent
        """
        @tool
        async def search_web(query: str, num_results: int = 5) -> Dict[str, Any]:
            """
            Search the web for external information.

            Args:
                query: The search query
                num_results: Number of results to return

            Returns:
                Dictionary with search results and summaries
            """
            if not self.web_search_agent:
                return {
                    "error": "Web search agent not available",
                    "results": []
                }

            try:
                # Call the web search agent's search method
                results = await self.web_search_agent.search(
                    query=query,
                    num_results=num_results
                )
                return results
            except Exception as e:
                logger.error(f"Web search tool error: {e}")
                return {
                    "error": str(e),
                    "results": []
                }

        return search_web

    def _classify_intent(self, message: str) -> IntentType:
        """
        Classify user intent from the message.

        This is a simple heuristic-based classifier. In production,
        this could be replaced with an LLM-based classifier.

        Args:
            message: User message to classify

        Returns:
            IntentType enum value
        """
        message_lower = message.lower()

        # Web search indicators (check first - very specific domain)
        if any(term in message_lower for term in [
            "google", "search for", "find on web", "look up online",
            "current", "latest", "recent news", "today"
        ]):
            return IntentType.WEB_SEARCH

        # Exploration indicators (check second - broad/open-ended queries)
        # These are broader than specific questions but more general than summaries
        if any(term in message_lower for term in [
            "explore", "tell me about the world", "tell me about the lore",
            "tell me more about", "relationships between",
            "what can you tell me"  # "What can you tell me" is exploratory, not a specific question
        ]):
            return IntentType.EXPLORATION

        # Summary/analysis indicators (check third - specific analytical requests)
        if any(term in message_lower for term in [
            "summarize", "summary of", "analyze", "analysis",
            "explain", "overview", "provide an overview",
            "list all", "find all", "show me all", "character arc"
        ]):
            return IntentType.SUMMARY

        # Factual question indicators (check fourth - specific questions)
        # Questions starting with who, what, when, where, why, how
        # Note: Exploration queries checked first to catch broader patterns
        if any(message_lower.startswith(q) for q in [
            "who", "what", "when", "where", "why", "how",
            "is", "does", "can", "did"
        ]):
            return IntentType.QUESTION

        # Default to exploration for other open-ended queries
        return IntentType.EXPLORATION

    async def process(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and return a response.

        This is the main entry point for handling user queries. The orchestrator:
        1. Classifies user intent
        2. Retrieves conversation history if available
        3. Routes to appropriate sub-agent(s)
        4. Formats and returns response

        Args:
            message: User message/query
            conversation_id: Optional conversation ID for multi-turn chat
            context: Optional context dict with filters, mode, etc.

        Returns:
            Response dict containing:
                - content: Response text
                - intent: Classified intent
                - agent_used: List of agents invoked
                - sources: List of source citations
                - conversation_id: Conversation ID
                - metadata: Additional metadata

        Raises:
            FastAgentError: If agent processing fails

        Example:
            >>> response = await orchestrator.process(
            ...     message="Who is Frodo Baggins?",
            ...     conversation_id="conv_123"
            ... )
            >>> print(response["content"])
            "Frodo Baggins is a hobbit who..."
        """
        try:
            # Classify user intent
            intent = self._classify_intent(message)
            logger.info(f"Classified intent: {intent.value} for message: {message[:50]}...")

            # Get or create conversation history
            if conversation_id:
                history = self.conversation_history.get(conversation_id, [])
            else:
                history = []
                conversation_id = self._generate_conversation_id()

            # Add user message to history
            history.append({"role": "user", "content": message})

            # Route based on intent
            agents_used = []
            sources = []
            response_content = ""

            if intent in [IntentType.QUESTION, IntentType.EXPLORATION]:
                # Use retrieval agent for factual questions
                if self.retrieval_agent:
                    logger.info("Routing to retrieval agent")
                    retrieval_results = await self._call_retrieval_agent(message, context)
                    sources.extend(retrieval_results.get("sources", []))
                    response_content = retrieval_results.get("content", "")
                    agents_used.append("retrieval")
                else:
                    logger.warning("Retrieval agent not available")
                    response_content = "Retrieval agent is not available. Please try again later."

            elif intent == IntentType.SUMMARY:
                # Use both retrieval and analyst
                if self.retrieval_agent:
                    logger.info("Routing to retrieval agent for context")
                    retrieval_results = await self._call_retrieval_agent(message, context)
                    sources.extend(retrieval_results.get("sources", []))
                    agents_used.append("retrieval")

                if self.analyst_agent:
                    logger.info("Routing to analyst agent for summarization")
                    # Pass retrieval context to analyst
                    analyst_context = {
                        "sources": sources,
                        "query": message
                    }
                    analyst_results = await self._call_analyst_agent(message, analyst_context)
                    response_content = analyst_results.get("content", "")
                    agents_used.append("analyst")
                else:
                    # Fallback: use retrieval results directly
                    response_content = retrieval_results.get("content", "")

            elif intent == IntentType.WEB_SEARCH:
                # Use web search agent
                if self.web_search_agent:
                    logger.info("Routing to web search agent")
                    search_results = await self._call_web_search_agent(message, context)
                    response_content = search_results.get("content", "")
                    sources.extend(search_results.get("sources", []))
                    agents_used.append("web_search")
                else:
                    logger.warning("Web search agent not available")
                    response_content = "Web search is not available. Please try asking about documents in the database."

            else:
                # Fallback for unknown intent
                response_content = "I'm not sure how to help with that. Could you rephrase your question?"

            # Add assistant response to history
            history.append({"role": "assistant", "content": response_content})
            self.conversation_history[conversation_id] = history

            # Build response
            response = OrchestratorResponse(
                content=response_content,
                intent=intent,
                agent_used=agents_used,
                sources=sources,
                conversation_id=conversation_id,
                metadata={
                    "message_count": len(history),
                    "model": self.model
                }
            )

            return response.to_dict()

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise FastAgentError(f"Failed to process message: {e}")

    async def _call_retrieval_agent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call the retrieval agent for document search.

        Args:
            query: Search query
            context: Optional context (filters, limits, etc.)

        Returns:
            Dict with content and sources
        """
        if not self.retrieval_agent:
            return {"content": "", "sources": []}

        try:
            # Use FastAgent tool if agent is initialized, otherwise call directly
            if hasattr(self, 'agent') and self.agent:
                # Let FastAgent orchestrator handle the tool call
                # This is a fallback - normally the agent would call this via process()
                pass

            # Direct call to retrieval agent (used when called from legacy code)
            results = await self.retrieval_agent.search(query, limit=5)

            # Format results
            if results:
                content = self._format_retrieval_results(results)
                # Build sources list - handle both dict and object results
                sources = []
                for r in results[:5]:  # Limit to top 5 sources
                    if isinstance(r, dict):
                        # Handle dict results
                        sources.append({
                            "document_id": r.get("document_id", ""),
                            "document_title": r.get("document_title", "Unknown"),
                            "chunk_id": r.get("chunk_id", ""),
                            "page": r.get("page"),
                            "text": r.get("text", "")[:200] + ("..." if len(r.get("text", "")) > 200 else ""),
                            "score": r.get("score", 0)
                        })
                    else:
                        # Handle object results
                        text = r.text if hasattr(r, "text") else ""
                        sources.append({
                            "document_id": r.document_id if hasattr(r, "document_id") else "",
                            "document_title": (r.document_title if hasattr(r, "document_title") else None) or "Unknown",
                            "chunk_id": r.chunk_id if hasattr(r, "chunk_id") else "",
                            "page": r.page if hasattr(r, "page") else None,
                            "text": text[:200] + "..." if len(text) > 200 else text,
                            "score": r.score if hasattr(r, "score") else 0
                        })
                return {"content": content, "sources": sources}
            else:
                return {
                    "content": "I couldn't find any relevant information in the documents.",
                    "sources": []
                }

        except Exception as e:
            logger.error(f"Retrieval agent call failed: {e}")
            return {"content": f"Retrieval failed: {e}", "sources": []}

    async def _call_analyst_agent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call the analyst agent for summarization/analysis.

        This method invokes the analyst sub-agent to perform deep analysis
        on the provided query and context. The analyst can summarize content,
        extract entities, identify themes, and provide creative insights.

        Args:
            query: Analysis query (e.g., "Summarize Gandalf's character arc")
            context: Optional context containing:
                - sources: List of source documents to analyze
                - analysis_type: Specific type of analysis requested
                - Any other contextual information

        Returns:
            Dict containing:
                - content (str): Analysis result text
                - sources (List[Dict]): Source references used in analysis
            Returns {"content": ""} if analyst agent not available.

        Example:
            >>> result = await self._call_analyst_agent(
            ...     query="Analyze the theme of power",
            ...     context={"sources": retrieval_results}
            ... )
            >>> print(result["content"])
        """
        if not self.analyst_agent:
            return {"content": ""}

        try:
            # Use analyst agent's analyze method
            # The FastAgent tool wrapper handles this when called from the agent
            result = await self.analyst_agent.analyze(
                query=query,
                analysis_type="summary"
            )
            return {
                "content": result.get("analysis", ""),
                "sources": result.get("sources", [])
            }

        except Exception as e:
            logger.error(f"Analyst agent call failed: {e}")
            return {"content": f"Analysis failed: {e}"}

    async def _call_web_search_agent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call the web search agent for external search.

        This method invokes the web search sub-agent to search external sources
        when information is not available in the document database. The agent
        optimizes queries, filters results, and generates summaries with citations.

        Args:
            query: Search query (e.g., "What was Tolkien's inspiration for LOTR?")
            context: Optional context containing:
                - max_results: Maximum number of search results
                - search_engine: Preferred search engine (duckduckgo, brave)
                - filters: Domain filters or other search constraints

        Returns:
            Dict containing:
                - content (str): Summarized search findings
                - sources (List[Dict]): Web sources with URLs and snippets
            Returns {"content": "", "sources": []} if web search agent not available.

        Example:
            >>> result = await self._call_web_search_agent(
            ...     query="Latest news about Middle-earth adaptations",
            ...     context={"max_results": 5}
            ... )
            >>> for source in result["sources"]:
            ...     print(f"{source['title']}: {source['url']}")
        """
        if not self.web_search_agent:
            return {"content": "", "sources": []}

        try:
            # Use web search agent's search method
            # The FastAgent tool wrapper handles this when called from the agent
            result = await self.web_search_agent.search(
                query=query,
                num_results=5
            )
            return {
                "content": result.get("summary", ""),
                "sources": result.get("sources", [])
            }

        except Exception as e:
            logger.error(f"Web search agent call failed: {e}")
            return {"content": f"Web search failed: {e}", "sources": []}

    def _format_retrieval_results(self, results: List[Any]) -> str:
        """
        Format retrieval results into a coherent response.

        Args:
            results: List of SearchResult objects or dicts with text/page

        Returns:
            Formatted response string
        """
        if not results:
            return "No relevant information found."

        # Build response from top results
        response_parts = []
        for i, result in enumerate(results[:3], 1):  # Top 3 results
            # Handle both dict and object types
            if isinstance(result, dict):
                text = result.get("text", "")
                page = result.get("page")
            else:
                text = result.text if hasattr(result, "text") else ""
                page = result.page if hasattr(result, "page") else None

            page_info = f" (Page {page})" if page else ""
            response_parts.append(
                f"{i}. {text}{page_info}"
            )

        return "\n\n".join(response_parts)

    def _generate_conversation_id(self) -> str:
        """Generate a unique conversation ID."""
        import uuid
        return f"conv_{uuid.uuid4().hex[:8]}"

    def add_to_conversation(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> None:
        """
        Add a message to conversation history.

        Maintains conversation context for multi-turn dialogues. Messages are
        stored chronologically and can be used by the orchestrator to understand
        context in follow-up questions.

        Args:
            conversation_id: Unique conversation identifier
            role: Message role, either "user" or "assistant"
            content: Message content text

        Example:
            >>> orchestrator = OrchestratorAgent()
            >>> conv_id = "conv_abc123"
            >>> orchestrator.add_to_conversation(conv_id, "user", "Who is Gandalf?")
            >>> orchestrator.add_to_conversation(conv_id, "assistant", "Gandalf is...")
            >>> history = orchestrator.get_conversation(conv_id)
            >>> print(f"Messages: {len(history)}")  # 2
        """
        # Initialize conversation if it doesn't exist
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []

        # Add message with role and content
        # Format matches FastAgent/OpenAI message structure
        message = {
            "role": role,      # "user" or "assistant"
            "content": content  # Message text
        }

        self.conversation_history[conversation_id].append(message)

        # Optionally truncate very long conversations to stay within context window
        # Keep last MAX_HISTORY_LENGTH messages to prevent token overflow
        if len(self.conversation_history[conversation_id]) > self.max_history_length:
            # Remove oldest messages, keep most recent
            self.conversation_history[conversation_id] = \
                self.conversation_history[conversation_id][-self.max_history_length:]

            logger.debug(
                f"Truncated conversation {conversation_id} to "
                f"{self.max_history_length} messages"
            )

        logger.debug(
            f"Added {role} message to conversation {conversation_id} "
            f"({len(self.conversation_history[conversation_id])} total messages)"
        )

    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear conversation history for a given ID.

        Args:
            conversation_id: Conversation ID to clear

        Returns:
            True if cleared, False if not found
        """
        if conversation_id in self.conversation_history:
            del self.conversation_history[conversation_id]
            logger.info(f"Cleared conversation: {conversation_id}")
            return True
        return False

    def get_conversation(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a given ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of message dicts with role and content
        """
        return self.conversation_history.get(conversation_id, [])

    # Private method aliases for test compatibility
    def _add_to_history(self, conversation_id: str, role: str, content: str) -> None:
        """Alias for add_to_conversation for test compatibility."""
        self.add_to_conversation(conversation_id, role, content)

    def _get_conversation_history(
        self,
        conversation_id: str,
        max_length: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Alias for get_conversation with optional max_length parameter.

        Args:
            conversation_id: Conversation ID
            max_length: Optional maximum total characters (truncates from end if exceeded)

        Returns:
            List of message dicts, optionally truncated by character count
        """
        history = self.get_conversation(conversation_id)

        if not max_length:
            return history

        # Truncate by character count from the most recent messages
        # Work backwards from the end, keeping messages until we exceed max_length
        truncated = []
        total_chars = 0

        for msg in reversed(history):
            msg_length = len(msg["content"])
            if total_chars + msg_length <= max_length:
                truncated.insert(0, msg)  # Insert at beginning to maintain order
                total_chars += msg_length
            else:
                break  # Stop adding messages once we'd exceed the limit

        return truncated

    def _clear_conversation_history(self, conversation_id: str) -> None:
        """Alias for clear_conversation for test compatibility."""
        self.clear_conversation(conversation_id)
