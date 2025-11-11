"""
FastAgent agents for Buddharauer V2.

This package contains all FastAgent agent implementations for the multi-agent
RAG system. Each agent specializes in a specific task and can be composed
together via the orchestrator agent.

Agents:
    - Orchestrator: Main routing agent (llama3.2:latest)
    - Retrieval: Document search and RAG (qwen2.5:latest)
    - Analyst: Summarization and thematic analysis (llama3.2:latest)
    - WebSearch: External web search (mistral:7b)

Architecture:
    User → FastAPI → Orchestrator → [Retrieval | Analyst | WebSearch] → Response

Usage:
    >>> from src.agents import create_all_agents
    >>> agents = create_all_agents()
    >>> orchestrator = agents["orchestrator"]
    >>> response = orchestrator.run("Who is Aragorn?")
"""

from typing import Dict, Any, Optional
import logging

# Import agent factory functions from fastagent_client
from src.utils.fastagent_client import (
    create_orchestrator_agent,
    create_retrieval_agent,
    create_analyst_agent,
    create_websearch_agent,
    initialize_fastagent,
    setup_fastagent,
    FastAgentError
)

logger = logging.getLogger(__name__)

__all__ = [
    "create_orchestrator_agent",
    "create_retrieval_agent",
    "create_analyst_agent",
    "create_websearch_agent",
    "create_all_agents",
    "initialize_fastagent",
    "setup_fastagent",
    "FastAgentError",
]


def create_all_agents(
    init_fastagent: bool = True,
    skip_missing: bool = False
) -> Dict[str, Any]:
    """
    Create all FastAgent agents for the system.

    Convenience function that initializes FastAgent and creates all four
    agents needed for the complete multi-agent system.

    Args:
        init_fastagent: If True, initialize FastAgent environment first.
        skip_missing: If True, skip agents whose models aren't available
                      instead of raising errors.

    Returns:
        Dictionary mapping agent names to Agent instances:
        {
            "orchestrator": Agent,
            "retrieval": Agent,
            "analyst": Agent,
            "websearch": Agent
        }

    Raises:
        FastAgentError: If FastAgent initialization or agent creation fails
                        (unless skip_missing=True)

    Example:
        >>> agents = create_all_agents()
        >>> orchestrator = agents["orchestrator"]
        >>> retrieval = agents["retrieval"]
    """
    agents = {}

    # Initialize FastAgent if requested
    if init_fastagent:
        try:
            initialize_fastagent(verify_connection=True)
        except FastAgentError as e:
            logger.error(f"Failed to initialize FastAgent: {e}")
            if not skip_missing:
                raise
            return agents

    # Create orchestrator (required)
    try:
        agents["orchestrator"] = create_orchestrator_agent()
        logger.info("Created orchestrator agent")
    except FastAgentError as e:
        logger.error(f"Failed to create orchestrator: {e}")
        if not skip_missing:
            raise

    # Create retrieval agent (required for RAG)
    try:
        agents["retrieval"] = create_retrieval_agent()
        logger.info("Created retrieval agent")
    except FastAgentError as e:
        logger.error(f"Failed to create retrieval agent: {e}")
        if not skip_missing:
            raise

    # Create analyst agent (optional)
    try:
        agents["analyst"] = create_analyst_agent()
        logger.info("Created analyst agent")
    except FastAgentError as e:
        logger.warning(f"Failed to create analyst agent: {e}")
        if not skip_missing:
            raise

    # Create websearch agent (optional)
    try:
        agents["websearch"] = create_websearch_agent()
        logger.info("Created websearch agent")
    except FastAgentError as e:
        logger.warning(f"Failed to create websearch agent: {e}")
        if not skip_missing:
            raise

    logger.info(f"Created {len(agents)} agents successfully")
    return agents
