"""
Chat endpoint for conversational interactions with documents.

This module provides the main chat interface for the Buddharauer system.
Users send messages and receive AI-generated responses with source citations.

The chat endpoint:
    1. Logs the user query to QueryLogger
    2. Invokes FastAgent orchestrator for intelligent routing
    3. Orchestrator routes to appropriate agent (Retrieval, Analyst, WebSearch)
    4. Returns formatted response with sources and metadata

Architecture Flow:
    User Message → QueryLogger → Orchestrator → [Retrieval | Analyst | WebSearch] → Response

Usage Example:
    POST /api/chat
    {
        "message": "Who is Aragorn?",
        "conversation_id": "session_123",
        "user_id": "faraday"
    }

Response:
    {
        "response": "Aragorn is a ranger...",
        "sources": [...],
        "conversation_id": "session_123",
        "agent_used": ["orchestrator", "retrieval"],
        "processing_time_ms": 1234.5
    }
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import time

from src.api.models.requests import ChatRequest
from src.api.models.responses import ChatResponse, SourceReference, ErrorResponse
from src.api.dependencies import get_vector_store, get_document_registry, get_query_logger
from src.utils.logging import get_logger

# Import agent classes for FastAgent integration
from src.agents import OrchestratorAgent, RetrievalAgent, AnalystAgent, WebSearchAgent

logger = get_logger(__name__)

# Global agent instances (initialized on startup)
# These will be initialized by the FastAPI app startup event
_orchestrator: Optional[OrchestratorAgent] = None
_retrieval_agent: Optional[RetrievalAgent] = None
_analyst_agent: Optional[AnalystAgent] = None
_web_search_agent: Optional[WebSearchAgent] = None

# Create router for chat endpoints
router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


async def initialize_agents(
    vector_store,
    document_registry
):
    """
    Initialize all FastAgent agents on application startup.

    This function creates and initializes the orchestrator and all sub-agents.
    Should be called from the FastAPI startup event handler.

    Args:
        vector_store: VectorStore instance for retrieval agent
        document_registry: DocumentRegistry instance for document metadata

    Note:
        This sets the global agent instances (_orchestrator, _retrieval_agent, etc.)
        which are then used by the chat endpoint.
    """
    global _orchestrator, _retrieval_agent, _analyst_agent, _web_search_agent

    try:
        logger.info("Initializing FastAgent agents...")

        # Create retrieval agent with vector store
        _retrieval_agent = RetrievalAgent(
            vector_store=vector_store,
            document_registry=document_registry
        )
        await _retrieval_agent.initialize()
        logger.info("✓ Retrieval agent initialized")

        # Create analyst agent
        _analyst_agent = AnalystAgent()
        await _analyst_agent.initialize()
        logger.info("✓ Analyst agent initialized")

        # Create web search agent
        _web_search_agent = WebSearchAgent()
        await _web_search_agent.initialize()
        logger.info("✓ Web search agent initialized")

        # Create orchestrator with sub-agents
        _orchestrator = OrchestratorAgent()
        await _orchestrator.initialize(
            retrieval_agent=_retrieval_agent,
            analyst_agent=_analyst_agent,
            web_search_agent=_web_search_agent
        )
        logger.info("✓ Orchestrator agent initialized")

        logger.info("All FastAgent agents initialized successfully!")

    except Exception as e:
        logger.error(f"Failed to initialize agents: {e}", exc_info=True)
        # Don't fail startup, but log the error
        # Chat endpoint will fall back to basic retrieval if orchestrator is None


def get_orchestrator() -> Optional[OrchestratorAgent]:
    """
    Get the global orchestrator agent instance.

    Returns:
        OrchestratorAgent instance or None if not initialized

    Note:
        If orchestrator is not available, the chat endpoint will fall back
        to basic retrieval (Phase 2 behavior).
    """
    return _orchestrator


@router.post("", response_model=ChatResponse, status_code=200)
async def chat(
    request: ChatRequest,
    vector_store = Depends(get_vector_store),
    registry = Depends(get_document_registry),
    query_logger = Depends(get_query_logger)
):
    """
    Process a chat message and return an AI-generated response.

    This endpoint handles multi-turn conversations with intelligent document retrieval.
    Currently uses direct vector search; will integrate FastAgent orchestrator in Phase 3.

    Phase 3 Implementation (Current):
        1. Log user query to QueryLogger
        2. Call FastAgent orchestrator
        3. Orchestrator routes to appropriate agent (analyst, retrieval, web_search)
        4. Generate sophisticated response with multi-source synthesis
        5. Log response and return

    Fallback (if orchestrator unavailable):
        1. Log user query
        2. Perform direct semantic search (Phase 2 behavior)
        3. Generate simple response from top results
        4. Log response and return

    Args:
        request: ChatRequest with message, conversation_id, and optional context
        vector_store: VectorStore instance (injected dependency)
        registry: DocumentRegistry instance (injected dependency)
        query_logger: QueryLogger instance (injected dependency)

    Returns:
        ChatResponse: AI response with sources and metadata

    Raises:
        HTTPException 400: Invalid request (empty message)
        HTTPException 500: Processing failed

    Example Request:
        ```json
        {
            "message": "Who is Gandalf?",
            "conversation_id": "session_abc123",
            "user_id": "faraday",
            "context": {
                "documents": ["fellowship"],
                "mode": "explanatory"
            }
        }
        ```

    Example Response:
        ```json
        {
            "response": "Based on the available documents, Gandalf is...",
            "sources": [
                {
                    "document_id": "doc_001",
                    "document_title": "Fellowship of the Ring",
                    "chunk_id": "doc_001_chunk_100",
                    "page": 100,
                    "text": "Gandalf the Grey was one of the Istari...",
                    "relevance_score": 0.92
                }
            ],
            "conversation_id": "session_abc123",
            "agent_used": "retrieval",
            "processing_time_ms": 856.3,
            "metadata": {"query_type": "question"}
        }
        ```

    Note:
        - This is a Phase 2 implementation using basic RAG
        - Phase 3 will replace this with FastAgent orchestrator integration
        - Conversation history tracking is implemented but not yet used for context
    """
    start_time = time.time()

    try:
        # Validate message
        if not request.message or not request.message.strip():
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error="ValidationError",
                    message="Message cannot be empty",
                    details={"field": "message"}
                ).model_dump()
            )

        logger.info(
            f"Chat request: session={request.conversation_id}, "
            f"user={request.user_id}, message='{request.message[:50]}...'"
        )

        # Log the query to QueryLogger for analytics
        query_id = await query_logger.log_query(
            session_id=request.conversation_id,
            query=request.message,
            query_type="question",  # TODO: Infer query type in Phase 3
            user_id=request.user_id,
            metadata=request.context
        )

        # Get orchestrator instance
        orchestrator = get_orchestrator()

        # Phase 3: Use orchestrator if available, otherwise fall back to Phase 2
        if orchestrator is not None:
            # PHASE 3: FastAgent Orchestrator Integration
            logger.info("Using FastAgent orchestrator for response generation")

            try:
                # Call orchestrator with message and context
                orchestrator_response = await orchestrator.process(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    context=request.context
                )

                # Extract response components
                response_text = orchestrator_response["content"]
                agent_list = orchestrator_response.get("agent_used", ["orchestrator"])

                # Convert orchestrator sources to SourceReference objects
                sources: List[SourceReference] = []
                for src in orchestrator_response.get("sources", []):
                    sources.append(SourceReference(
                        document_id=src.get("document_id", "unknown"),
                        document_title=src.get("document_title", "Unknown Document"),
                        chunk_id=src.get("chunk_id", ""),
                        page=src.get("page"),
                        text=src.get("text", ""),
                        relevance_score=src.get("score", 0.0)
                    ))

                agent_used = "orchestrator" if len(agent_list) > 1 else agent_list[0]
                implementation_phase = "3"

            except Exception as orchestrator_error:
                # If orchestrator fails, fall back to Phase 2
                logger.error(
                    f"Orchestrator failed, falling back to Phase 2: {orchestrator_error}",
                    exc_info=True
                )
                orchestrator = None  # Trigger fallback below

        if orchestrator is None:
            # PHASE 2 FALLBACK: Direct vector search
            logger.warning("Orchestrator not available - using Phase 2 fallback")

            search_results = await vector_store.search(
                query_texts=[request.message],
                n_results=5,  # Top 5 most relevant chunks
                where=request.context.get("filters") if request.context else None
            )

            # Convert search results to SourceReference objects
            sources: List[SourceReference] = []
            for result in search_results:
                doc_id = result.get("metadata", {}).get("document_id")
                doc_title = None

                # Enrich with document title from registry
                if doc_id:
                    doc_record = await registry.get_by_id(doc_id)
                    if doc_record:
                        doc_title = doc_record.filename

                sources.append(SourceReference(
                    document_id=doc_id or "unknown",
                    document_title=doc_title or "Unknown Document",
                    chunk_id=result.get("id", ""),
                    page=result.get("metadata", {}).get("page"),
                    text=result.get("text", ""),
                    relevance_score=result.get("score", 0.0)
                ))

            # Generate simple response from top results (Phase 2 behavior)
            if sources:
                response_text = (
                    f"Based on the available documents:\n\n{sources[0].text}\n\n"
                    f"(Using Phase 2 fallback - orchestrator not available)"
                )
            else:
                response_text = (
                    "I couldn't find relevant information in the indexed documents. "
                    "Please try rephrasing your question or ensure documents are processed."
                )

            agent_used = "retrieval"
            implementation_phase = "2"

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        # Log the response to QueryLogger
        await query_logger.log_response(
            query_id=query_id,
            response=response_text,
            sources=[
                {
                    "document_id": src.document_id,
                    "chunk_id": src.chunk_id,
                    "page": src.page,
                    "score": src.relevance_score
                }
                for src in sources
            ],
            agent_used=agent_used,
            processing_time_ms=int(processing_time_ms),
            success=True
        )

        logger.info(
            f"Chat response generated (Phase {implementation_phase}): "
            f"agent={agent_used}, sources={len(sources)}, "
            f"time={processing_time_ms:.2f}ms"
        )

        # Return chat response
        return ChatResponse(
            response=response_text,
            sources=sources,
            conversation_id=request.conversation_id,
            agent_used=agent_used,
            processing_time_ms=processing_time_ms,
            metadata={
                "query_type": "question",
                "phase": implementation_phase,
                "implementation": "fastagent" if implementation_phase == "3" else "basic_rag"
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Chat processing failed: {e}", exc_info=True)

        # Log the failure to QueryLogger if we have a query_id
        # Note: query_id might not exist if error occurred before logging
        try:
            if 'query_id' in locals():
                await query_logger.log_response(
                    query_id=query_id,
                    response="",
                    sources=[],
                    agent_used="retrieval",
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    success=False,
                    error_message=str(e)
                )
        except Exception as log_error:
            logger.error(f"Failed to log error: {log_error}")

        # Return error response
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="ChatError",
                message="Failed to process chat message",
                details={
                    "conversation_id": request.conversation_id,
                    "error": str(e)
                }
            ).model_dump()
        )


@router.get("/conversations/{conversation_id}", status_code=200)
async def get_conversation_history(
    conversation_id: str,
    limit: int = 50,
    query_logger = Depends(get_query_logger)
):
    """
    Retrieve conversation history for a given session.

    This endpoint fetches past messages and responses for a conversation,
    useful for:
        - Displaying chat history in the UI
        - Context reconstruction for multi-turn conversations
        - User session analysis

    Args:
        conversation_id: Unique conversation/session identifier
        limit: Maximum number of messages to return (default: 50)
        query_logger: QueryLogger instance (injected dependency)

    Returns:
        Dict with conversation history and metadata

    Raises:
        HTTPException 404: Conversation not found
        HTTPException 500: Retrieval failed

    Example:
        ```bash
        curl http://localhost:8000/api/chat/conversations/session_123?limit=20
        ```

    Response:
        ```json
        {
            "conversation_id": "session_123",
            "messages": [
                {
                    "query": "Who is Aragorn?",
                    "response": "Aragorn is a ranger...",
                    "timestamp": "2025-01-15T14:23:01Z",
                    "sources": [...]
                }
            ],
            "total_messages": 5,
            "returned": 5
        }
        ```
    """
    try:
        logger.info(f"Fetching conversation history: {conversation_id}")

        # Retrieve conversation history from QueryLogger
        history = await query_logger.get_by_session(
            session_id=conversation_id,
            limit=limit
        )

        # Convert QueryRecord objects to dict format
        messages = [record.to_dict() for record in history]

        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "total_messages": len(messages),
            "returned": len(messages)
        }

    except Exception as e:
        logger.error(
            f"Failed to retrieve conversation {conversation_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="ConversationError",
                message="Failed to retrieve conversation history",
                details={
                    "conversation_id": conversation_id,
                    "error": str(e)
                }
            ).model_dump()
        )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def clear_conversation(
    conversation_id: str,
    query_logger = Depends(get_query_logger)
):
    """
    Clear/delete a conversation and all its messages.

    This permanently removes all chat history for a conversation.
    Cannot be undone.

    Args:
        conversation_id: Unique conversation/session identifier
        query_logger: QueryLogger instance (injected dependency)

    Returns:
        No content (204 status)

    Raises:
        HTTPException 500: Deletion failed

    Example:
        ```bash
        curl -X DELETE http://localhost:8000/api/chat/conversations/session_123
        ```

    Warning:
        This operation is irreversible. All conversation data will be
        permanently deleted.
    """
    try:
        logger.info(f"Clearing conversation: {conversation_id}")

        # Clear conversation from QueryLogger
        await query_logger.clear_session(conversation_id)

        logger.info(f"Conversation cleared: {conversation_id}")
        return None  # 204 No Content

    except Exception as e:
        logger.error(
            f"Failed to clear conversation {conversation_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="ConversationError",
                message="Failed to clear conversation",
                details={
                    "conversation_id": conversation_id,
                    "error": str(e)
                }
            ).model_dump()
        )
