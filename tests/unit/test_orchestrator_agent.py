"""
Unit tests for Orchestrator Agent.

Tests the OrchestratorAgent class including initialization, intent classification,
tool routing, conversation management, and response formatting.

Test Coverage:
    - Agent initialization and setup
    - FastAgent instance creation
    - Intent classification
    - Sub-agent tool creation and routing
    - Conversation history management
    - Response formatting
    - Error handling and graceful degradation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import asdict

# Import module under test
from src.agents.orchestrator import (
    OrchestratorAgent,
    OrchestratorResponse,
    IntentType
)


class TestOrchestratorAgentInitialization:
    """Tests for Orchestrator Agent initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        agent = OrchestratorAgent()

        assert agent.model == "generic.llama3.2:latest"
        assert agent.temperature == 0.7
        assert agent.max_context_length == 4096
        assert agent.agent is None  # Not initialized yet
        assert agent.conversation_history == {}
        assert agent.retrieval_agent is None
        assert agent.analyst_agent is None
        assert agent.web_search_agent is None

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        agent = OrchestratorAgent(
            model="generic.custom:latest",
            temperature=0.5,
            max_context_length=2048
        )

        assert agent.model == "generic.custom:latest"
        assert agent.temperature == 0.5
        assert agent.max_context_length == 2048

    @patch('src.agents.orchestrator.FASTAGENT_AVAILABLE', True)
    @patch('src.agents.orchestrator.Agent')
    @patch('src.agents.orchestrator.initialize_fastagent')
    @pytest.mark.asyncio
    async def test_initialize_agent_with_all_subagents(
        self, mock_init_fa, mock_agent_class
    ):
        """Test agent initialization with all sub-agents provided."""
        # Mock FastAgent instance
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock sub-agents
        mock_retrieval = AsyncMock()
        mock_analyst = AsyncMock()
        mock_websearch = AsyncMock()

        # Create and initialize orchestrator
        agent = OrchestratorAgent()
        await agent.initialize(
            retrieval_agent=mock_retrieval,
            analyst_agent=mock_analyst,
            web_search_agent=mock_websearch
        )

        # Verify sub-agents stored
        assert agent.retrieval_agent == mock_retrieval
        assert agent.analyst_agent == mock_analyst
        assert agent.web_search_agent == mock_websearch

        # Verify FastAgent initialization called
        mock_init_fa.assert_called_once_with(verify_connection=False)

        # Verify Agent created with correct parameters
        mock_agent_class.assert_called_once()
        call_kwargs = mock_agent_class.call_args.kwargs
        assert call_kwargs["name"] == "orchestrator"
        assert call_kwargs["model"] == "generic.llama3.2:latest"
        assert call_kwargs["temperature"] == 0.7
        assert "system_prompt" in call_kwargs
        assert len(call_kwargs["tools"]) == 3  # All 3 sub-agents

    @patch('src.agents.orchestrator.FASTAGENT_AVAILABLE', True)
    @patch('src.agents.orchestrator.Agent')
    @patch('src.agents.orchestrator.initialize_fastagent')
    @pytest.mark.asyncio
    async def test_initialize_agent_with_partial_subagents(
        self, mock_init_fa, mock_agent_class
    ):
        """Test initialization with only some sub-agents."""
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Only provide retrieval agent
        mock_retrieval = AsyncMock()

        agent = OrchestratorAgent()
        await agent.initialize(retrieval_agent=mock_retrieval)

        # Verify only retrieval agent stored
        assert agent.retrieval_agent == mock_retrieval
        assert agent.analyst_agent is None
        assert agent.web_search_agent is None

        # Should have only 1 tool
        call_kwargs = mock_agent_class.call_args.kwargs
        assert len(call_kwargs["tools"]) == 1

    @patch('src.agents.orchestrator.FASTAGENT_AVAILABLE', False)
    @pytest.mark.asyncio
    async def test_initialize_without_fastagent(self):
        """Test initialization fails when FastAgent not available."""
        agent = OrchestratorAgent()

        with pytest.raises(ImportError, match="FastAgent is not available"):
            await agent.initialize()

    @patch('src.agents.orchestrator.FASTAGENT_AVAILABLE', True)
    @patch('src.agents.orchestrator.initialize_fastagent')
    @pytest.mark.asyncio
    async def test_initialize_handles_errors(self, mock_init_fa):
        """Test initialization handles errors gracefully."""
        # Mock initialization failure
        mock_init_fa.side_effect = Exception("Connection failed")

        agent = OrchestratorAgent()

        from src.utils.fastagent_client import FastAgentError
        with pytest.raises(FastAgentError, match="Orchestrator initialization failed"):
            await agent.initialize()


class TestIntentClassification:
    """Tests for intent classification."""

    def test_classify_question_intent(self):
        """Test classifying factual question intent."""
        agent = OrchestratorAgent()

        # Questions that should be classified as QUESTION
        question_inputs = [
            "Who is Aragorn?",
            "What is the Ring of Power?",
            "Where is Mordor located?",
            "When did Frodo leave the Shire?"
        ]

        for question in question_inputs:
            intent = agent._classify_intent(question)
            assert intent == IntentType.QUESTION

    def test_classify_summary_intent(self):
        """Test classifying summary/analysis intent."""
        agent = OrchestratorAgent()

        summary_inputs = [
            "Summarize the Fellowship's journey",
            "Analyze Gandalf's character arc",
            "Provide an overview of the main themes"
        ]

        for summary in summary_inputs:
            intent = agent._classify_intent(summary)
            assert intent == IntentType.SUMMARY

    def test_classify_web_search_intent(self):
        """Test classifying web search intent."""
        agent = OrchestratorAgent()

        web_search_inputs = [
            "Search for Tolkien's inspiration",
            "Latest news about Lord of the Rings adaptations",
            "Look up online who played Aragorn"
        ]

        for query in web_search_inputs:
            intent = agent._classify_intent(query)
            assert intent == IntentType.WEB_SEARCH

    def test_classify_exploration_intent(self):
        """Test classifying open-ended exploration intent."""
        agent = OrchestratorAgent()

        exploration_inputs = [
            "Tell me about the world of Middle-earth",
            "Explore the relationships between characters",
            "What can you tell me about the lore?"
        ]

        for query in exploration_inputs:
            intent = agent._classify_intent(query)
            assert intent == IntentType.EXPLORATION


class TestConversationManagement:
    """Tests for conversation history management."""

    def test_add_to_conversation_history(self):
        """Test adding messages to conversation history."""
        agent = OrchestratorAgent()
        conv_id = "conv_123"

        # Add user message
        agent._add_to_history(conv_id, "user", "Who is Gandalf?")

        assert conv_id in agent.conversation_history
        assert len(agent.conversation_history[conv_id]) == 1
        assert agent.conversation_history[conv_id][0]["role"] == "user"
        assert agent.conversation_history[conv_id][0]["content"] == "Who is Gandalf?"

        # Add assistant response
        agent._add_to_history(conv_id, "assistant", "Gandalf is a wizard...")

        assert len(agent.conversation_history[conv_id]) == 2
        assert agent.conversation_history[conv_id][1]["role"] == "assistant"

    def test_get_conversation_history(self):
        """Test retrieving conversation history."""
        agent = OrchestratorAgent()
        conv_id = "conv_123"

        # Add messages
        agent._add_to_history(conv_id, "user", "Message 1")
        agent._add_to_history(conv_id, "assistant", "Response 1")
        agent._add_to_history(conv_id, "user", "Message 2")

        # Get history
        history = agent._get_conversation_history(conv_id)

        assert len(history) == 3
        assert history[0]["content"] == "Message 1"
        assert history[1]["content"] == "Response 1"
        assert history[2]["content"] == "Message 2"

    def test_get_empty_conversation_history(self):
        """Test getting history for non-existent conversation."""
        agent = OrchestratorAgent()

        history = agent._get_conversation_history("nonexistent_conv")

        assert history == []

    def test_clear_conversation_history(self):
        """Test clearing conversation history."""
        agent = OrchestratorAgent()
        conv_id = "conv_123"

        # Add messages
        agent._add_to_history(conv_id, "user", "Message")
        assert conv_id in agent.conversation_history

        # Clear
        agent._clear_conversation_history(conv_id)

        assert conv_id not in agent.conversation_history

    def test_context_window_truncation(self):
        """Test that conversation history respects context window limits."""
        agent = OrchestratorAgent(max_context_length=100)
        conv_id = "conv_123"

        # Add many messages
        for i in range(20):
            agent._add_to_history(conv_id, "user", f"Message {i}" * 10)
            agent._add_to_history(conv_id, "assistant", f"Response {i}" * 10)

        # Get truncated history
        history = agent._get_conversation_history(conv_id, max_length=100)

        # Should be truncated to fit context window
        total_length = sum(len(msg["content"]) for msg in history)
        assert total_length <= 100


class TestToolCreation:
    """Tests for sub-agent tool creation."""

    @pytest.mark.asyncio
    async def test_create_retrieval_tool(self):
        """Test creating retrieval agent tool."""
        # Mock retrieval agent
        mock_retrieval = AsyncMock()
        mock_retrieval.search = AsyncMock(return_value=[
            {
                "chunk_id": "chunk_001",
                "text": "Aragorn was a ranger",
                "score": 0.95
            }
        ])

        agent = OrchestratorAgent()
        agent.retrieval_agent = mock_retrieval

        # Create tool
        tool = agent._create_retrieval_tool()

        # Test tool invocation
        result = await tool("Who is Aragorn?", limit=5)

        # Verify retrieval agent was called
        mock_retrieval.search.assert_called_once_with(
            query="Who is Aragorn?",
            limit=5
        )

    @pytest.mark.asyncio
    async def test_create_analyst_tool(self):
        """Test creating analyst agent tool."""
        # Mock analyst agent
        mock_analyst = AsyncMock()
        mock_analyst.analyze = AsyncMock(return_value={
            "summary": "Gandalf is a wizard...",
            "entities": ["Gandalf", "Istari"],
            "themes": ["wisdom", "sacrifice"]
        })

        agent = OrchestratorAgent()
        agent.analyst_agent = mock_analyst

        # Create tool
        tool = agent._create_analyst_tool()

        # Test tool invocation
        result = await tool("Analyze Gandalf", analysis_type="character")

        # Verify analyst agent was called
        mock_analyst.analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_websearch_tool(self):
        """Test creating web search agent tool."""
        # Mock web search agent
        mock_websearch = AsyncMock()
        mock_websearch.search = AsyncMock(return_value={
            "summary": "Tolkien was inspired by...",
            "results": [
                {"title": "Tolkien Biography", "url": "http://example.com"}
            ]
        })

        agent = OrchestratorAgent()
        agent.web_search_agent = mock_websearch

        # Create tool
        tool = agent._create_websearch_tool()

        # Test tool invocation (note: tool uses num_results parameter)
        result = await tool("Tolkien inspiration", num_results=3)

        # Verify web search agent was called
        mock_websearch.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test tool handles errors gracefully."""
        # Mock retrieval agent that throws error
        mock_retrieval = AsyncMock()
        mock_retrieval.search = AsyncMock(side_effect=Exception("DB error"))

        agent = OrchestratorAgent()
        agent.retrieval_agent = mock_retrieval

        # Create tool
        tool = agent._create_retrieval_tool()

        # Tool should catch error and return error response
        result = await tool("query")

        assert "error" in result


class TestResponseProcessing:
    """Tests for response processing and formatting."""

    @pytest.mark.asyncio
    async def test_process_with_agent_mock(self):
        """Test processing a message with mocked FastAgent and retrieval agent."""
        agent = OrchestratorAgent()

        # Mock the FastAgent instance
        mock_agent_instance = AsyncMock()
        mock_agent_instance.run = AsyncMock(return_value=Mock(
            content="Aragorn is the heir to the throne of Gondor.",
            metadata={"sources": [{"page": 42}]}
        ))
        agent.agent = mock_agent_instance

        # Mock retrieval agent (needed for QUESTION intent)
        mock_retrieval = AsyncMock()
        mock_retrieval.search = AsyncMock(return_value=[
            {
                "text": "Aragorn is the heir to the throne of Gondor.",
                "page": 42,
                "document_title": "Fellowship of the Ring"
            }
        ])
        agent.retrieval_agent = mock_retrieval

        # Process message
        response = await agent.process(
            message="Who is Aragorn?",
            conversation_id="conv_123"
        )

        # Verify response structure (process returns dict, not OrchestratorResponse)
        assert isinstance(response, dict)
        assert "Aragorn" in response["content"]
        assert response["conversation_id"] == "conv_123"
        assert isinstance(response["sources"], list)

        # Verify retrieval agent was called (QUESTION intent uses retrieval)
        mock_retrieval.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_without_agent_fallback(self):
        """Test processing falls back gracefully when agent not initialized."""
        agent = OrchestratorAgent()
        # Don't initialize agent

        response = await agent.process("Who is Aragorn?")

        # Should return fallback response (as dict)
        assert isinstance(response, dict)
        assert "not initialized" in response["content"].lower() or \
               "unavailable" in response["content"].lower() or \
               "not available" in response["content"].lower()
        # Intent is stored as string in dict
        assert response["intent"] == IntentType.QUESTION.value or \
               response["intent"] == IntentType.UNKNOWN.value

    @pytest.mark.asyncio
    async def test_format_retrieval_results(self):
        """Test formatting retrieval results from vector search."""
        agent = OrchestratorAgent()

        results = [
            {
                "chunk_id": "chunk_001",
                "document_title": "Fellowship of the Ring",
                "page": 42,
                "text": "Aragorn was a ranger of the North..."
            },
            {
                "chunk_id": "chunk_002",
                "document_title": "The Two Towers",
                "page": 15,
                "text": "Aragorn led the fellowship..."
            }
        ]

        # Test the internal formatting method
        formatted = agent._format_retrieval_results(results)

        # Should include content from results
        assert "Aragorn" in formatted
        # Should include references to sources (page numbers or titles)
        assert "42" in formatted or "15" in formatted or \
               "Fellowship of the Ring" in formatted or "Two Towers" in formatted


class TestOrchestratorResponse:
    """Tests for OrchestratorResponse dataclass."""

    def test_create_response(self):
        """Test creating OrchestratorResponse instance."""
        response = OrchestratorResponse(
            content="Test response",
            intent=IntentType.QUESTION,
            agent_used=["retrieval"],
            sources=[{"page": 42}],
            conversation_id="conv_123",
            metadata={"processing_time": 1.5}
        )

        assert response.content == "Test response"
        assert response.intent == IntentType.QUESTION
        assert response.agent_used == ["retrieval"]
        assert len(response.sources) == 1
        assert response.conversation_id == "conv_123"
        assert response.metadata["processing_time"] == 1.5

    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = OrchestratorResponse(
            content="Test response",
            intent=IntentType.QUESTION,
            agent_used=["retrieval"],
            sources=[{"page": 42}]
        )

        response_dict = response.to_dict()

        assert response_dict["content"] == "Test response"
        assert response_dict["intent"] == "question"  # Enum to string
        assert response_dict["agent_used"] == ["retrieval"]
        assert response_dict["sources"] == [{"page": 42}]
        assert isinstance(response_dict["metadata"], dict)

    def test_response_optional_fields(self):
        """Test response with optional fields as None."""
        response = OrchestratorResponse(
            content="Test",
            intent=IntentType.QUESTION,
            agent_used=[],
            sources=[]
        )

        assert response.conversation_id is None
        assert response.metadata is None


class TestIntentTypeEnum:
    """Tests for IntentType enum."""

    def test_intent_type_values(self):
        """Test IntentType enum has expected values."""
        assert IntentType.QUESTION.value == "question"
        assert IntentType.SUMMARY.value == "summary"
        assert IntentType.EXPLORATION.value == "exploration"
        assert IntentType.WEB_SEARCH.value == "web_search"
        assert IntentType.CLARIFICATION.value == "clarification"
        assert IntentType.UNKNOWN.value == "unknown"

    def test_intent_type_comparison(self):
        """Test comparing IntentType values."""
        assert IntentType.QUESTION == IntentType.QUESTION
        assert IntentType.QUESTION != IntentType.SUMMARY


class TestSystemPromptBuilding:
    """Tests for system prompt construction."""

    def test_build_system_prompt(self):
        """Test building system prompt for orchestrator."""
        agent = OrchestratorAgent()

        prompt = agent._build_system_prompt()

        # Verify prompt contains key elements
        assert "Orchestrator" in prompt
        assert "Retrieval Agent" in prompt
        assert "Analyst Agent" in prompt
        assert "Web Search Agent" in prompt
        assert "citations" in prompt.lower()
        assert "context" in prompt.lower()

    def test_system_prompt_includes_routing_logic(self):
        """Test system prompt includes routing guidelines."""
        agent = OrchestratorAgent()

        prompt = agent._build_system_prompt()

        # Should describe when to use each sub-agent
        assert "factual questions" in prompt.lower() or "retrieval" in prompt.lower()
        assert "summarize" in prompt.lower() or "analysis" in prompt.lower()
        assert "external" in prompt.lower() or "web search" in prompt.lower()


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_handle_empty_message(self):
        """Test handling empty message input."""
        agent = OrchestratorAgent()
        agent.agent = AsyncMock()

        response = await agent.process(message="")

        # Should handle gracefully (returns dict)
        assert isinstance(response, dict)
        assert "content" in response

    @pytest.mark.asyncio
    async def test_handle_very_long_message(self):
        """Test handling very long message."""
        agent = OrchestratorAgent(max_context_length=100)
        agent.agent = AsyncMock()

        # Very long message
        long_message = "test " * 1000

        response = await agent.process(message=long_message)

        # Should truncate or handle appropriately (returns dict)
        assert isinstance(response, dict)
        assert "content" in response

    @pytest.mark.asyncio
    async def test_handle_special_characters(self):
        """Test handling messages with special characters."""
        agent = OrchestratorAgent()
        agent.agent = AsyncMock()

        special_chars_message = "Who is 'Aragorn'? <b>Bold</b> & \"quoted\""

        response = await agent.process(message=special_chars_message)

        # Should handle without errors (returns dict)
        assert isinstance(response, dict)
        assert "content" in response
