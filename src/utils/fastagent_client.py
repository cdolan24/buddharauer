"""
FastAgent client wrapper for Ollama integration.

Provides utility functions for initializing and managing FastAgent agents
with local Ollama models. This module handles environment setup, agent
creation, and configuration management for the multi-agent system.

Architecture:
    FastAgent Framework → Generic Provider → Ollama (localhost:11434/v1)

Agents:
    - Orchestrator: Main agent that routes queries to sub-agents (llama3.2)
    - Retrieval: Vector DB search and document retrieval (qwen2.5)
    - Analyst: Summarization and thematic analysis (llama3.2)
    - WebSearch: External web search via MCP tools (mistral:7b)

Usage:
    >>> from src.utils.fastagent_client import create_orchestrator_agent
    >>> orchestrator = create_orchestrator_agent()
    >>> response = orchestrator.run("Who is Aragorn?")
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# FastAgent imports (conditional to avoid import errors during testing)
try:
    from fastagent import Agent
    from fastagent.core import AgentConfig
    FASTAGENT_AVAILABLE = True
except ImportError:
    FASTAGENT_AVAILABLE = False
    logging.warning("FastAgent not available. Agent creation will fail.")

from src.utils.config import load_config

logger = logging.getLogger(__name__)

# Default Ollama configuration
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_API_KEY = "ollama"  # Placeholder, not validated by Ollama

# Configuration file path
CONFIG_PATH = Path(__file__).parent.parent.parent / "fastagent.config.yaml"


class FastAgentError(Exception):
    """Custom exception for FastAgent-related errors."""
    pass


def initialize_fastagent(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    verify_connection: bool = True
) -> None:
    """
    Initialize FastAgent environment variables for Ollama.

    Sets up the generic provider configuration to point to local Ollama
    instance. Must be called before creating any agents.

    Args:
        base_url: Ollama OpenAI-compatible API endpoint.
                  Defaults to http://localhost:11434/v1
        api_key: API key for generic provider (placeholder for Ollama).
                 Defaults to "ollama"
        verify_connection: If True, verify Ollama is accessible.

    Raises:
        FastAgentError: If Ollama is not accessible and verify_connection=True

    Example:
        >>> initialize_fastagent()
        >>> # Now agents can be created
    """
    if not FASTAGENT_AVAILABLE:
        raise FastAgentError(
            "FastAgent is not installed. Run: pip install fast-agent-mcp>=0.3.17"
        )

    # Set environment variables for generic provider
    os.environ["GENERIC_API_KEY"] = api_key or DEFAULT_API_KEY
    os.environ["GENERIC_BASE_URL"] = base_url or DEFAULT_OLLAMA_BASE_URL

    logger.info(
        f"FastAgent initialized with Ollama at {os.environ['GENERIC_BASE_URL']}"
    )

    # Verify Ollama connection if requested
    if verify_connection:
        try:
            import httpx
            response = httpx.get(
                base_url.replace("/v1", "/api/tags") if base_url else "http://localhost:11434/api/tags",
                timeout=5.0
            )
            if response.status_code != 200:
                raise FastAgentError(
                    f"Ollama not accessible at {base_url or DEFAULT_OLLAMA_BASE_URL}. "
                    "Make sure Ollama is running."
                )
            logger.info("Ollama connection verified successfully")
        except Exception as e:
            raise FastAgentError(
                f"Failed to connect to Ollama: {e}. "
                "Make sure Ollama is running (ollama serve)"
            )


def create_orchestrator_agent(
    model: str = "generic.llama3.2:latest",
    temperature: float = 0.7,
    system_prompt: Optional[str] = None
) -> "Agent":
    """
    Create the main orchestrator agent.

    The orchestrator is the primary agent that receives user queries,
    routes them to appropriate sub-agents, and synthesizes final responses.

    Args:
        model: FastAgent model specification (default: generic.llama3.2:latest)
        temperature: Sampling temperature 0.0-1.0 (default: 0.7)
        system_prompt: Custom system prompt. If None, uses default.

    Returns:
        FastAgent Agent instance configured as orchestrator

    Raises:
        FastAgentError: If FastAgent is not initialized or agent creation fails

    Example:
        >>> initialize_fastagent()
        >>> orchestrator = create_orchestrator_agent()
        >>> response = orchestrator.run("Tell me about Aragorn")
    """
    if not FASTAGENT_AVAILABLE:
        raise FastAgentError("FastAgent not available")

    # Ensure FastAgent is initialized
    if "GENERIC_BASE_URL" not in os.environ:
        initialize_fastagent()

    # Default system prompt for orchestrator
    if system_prompt is None:
        system_prompt = """You are an intelligent document Q&A assistant with access to a knowledge base of processed PDF documents.

Your role is to:
1. Understand user questions about the documents
2. Route queries to appropriate specialized agents (retrieval, analyst, web search)
3. Synthesize information from multiple sources
4. Provide clear, accurate, and well-cited responses

Always cite your sources with document titles and page numbers when available.
If you don't know something, say so rather than making assumptions."""

    try:
        agent = Agent(
            name="orchestrator",
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            tools=[]  # Sub-agents will be registered as tools
        )
        logger.info(f"Created orchestrator agent with model {model}")
        return agent
    except Exception as e:
        raise FastAgentError(f"Failed to create orchestrator agent: {e}")


def create_retrieval_agent(
    model: str = "generic.qwen2.5:latest",
    temperature: float = 0.5,
    system_prompt: Optional[str] = None
) -> "Agent":
    """
    Create the retrieval agent for document search.

    The retrieval agent specializes in semantic search over the vector
    database, query reformulation, and re-ranking results.

    Args:
        model: FastAgent model specification (default: generic.qwen2.5:latest)
               qwen2.5 recommended for better tool calling
        temperature: Sampling temperature 0.0-1.0 (default: 0.5)
        system_prompt: Custom system prompt. If None, uses default.

    Returns:
        FastAgent Agent instance configured for retrieval

    Raises:
        FastAgentError: If FastAgent is not initialized or agent creation fails

    Example:
        >>> retrieval = create_retrieval_agent()
        >>> # Agent will be registered as tool for orchestrator
    """
    if not FASTAGENT_AVAILABLE:
        raise FastAgentError("FastAgent not available")

    # Ensure FastAgent is initialized
    if "GENERIC_BASE_URL" not in os.environ:
        initialize_fastagent()

    # Default system prompt for retrieval
    if system_prompt is None:
        system_prompt = """You are a document retrieval specialist with access to a vector database of PDF documents.

Your role is to:
1. Understand user search queries
2. Reformulate queries for better semantic search
3. Search the vector database for relevant document chunks
4. Re-rank and filter results by relevance
5. Return the most relevant passages with metadata

Always preserve document metadata (title, page number, chapter) in your results.
Prioritize precision over recall - better to return fewer highly relevant results."""

    try:
        agent = Agent(
            name="retrieval",
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            tools=[]  # MCP tools for vector DB will be added
        )
        logger.info(f"Created retrieval agent with model {model}")
        return agent
    except Exception as e:
        raise FastAgentError(f"Failed to create retrieval agent: {e}")


def create_analyst_agent(
    model: str = "generic.llama3.2:latest",
    temperature: float = 0.5,
    system_prompt: Optional[str] = None
) -> "Agent":
    """
    Create the analyst agent for document analysis.

    The analyst agent specializes in summarization, thematic analysis,
    entity extraction, and generating insights from documents.

    Args:
        model: FastAgent model specification (default: generic.llama3.2:latest)
        temperature: Sampling temperature 0.0-1.0 (default: 0.5)
        system_prompt: Custom system prompt. If None, uses default.

    Returns:
        FastAgent Agent instance configured for analysis

    Raises:
        FastAgentError: If FastAgent is not initialized or agent creation fails

    Example:
        >>> analyst = create_analyst_agent()
        >>> # Agent will be registered as tool for orchestrator
    """
    if not FASTAGENT_AVAILABLE:
        raise FastAgentError("FastAgent not available")

    # Ensure FastAgent is initialized
    if "GENERIC_BASE_URL" not in os.environ:
        initialize_fastagent()

    # Default system prompt for analyst
    if system_prompt is None:
        system_prompt = """You are a document analysis specialist focused on extracting insights and patterns.

Your role is to:
1. Summarize long documents or passages
2. Identify key themes and topics
3. Extract important entities (people, places, events)
4. Generate creative insights and connections
5. Provide analytical perspectives on the content

Always ground your analysis in the actual text. Distinguish between what's explicitly stated and your inferences."""

    try:
        agent = Agent(
            name="analyst",
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            tools=[]  # Document access tools will be added
        )
        logger.info(f"Created analyst agent with model {model}")
        return agent
    except Exception as e:
        raise FastAgentError(f"Failed to create analyst agent: {e}")


def create_websearch_agent(
    model: str = "generic.mistral:7b",
    temperature: float = 0.3,
    system_prompt: Optional[str] = None
) -> "Agent":
    """
    Create the web search agent for external information.

    The web search agent handles queries that require external web search,
    formulates search queries, and summarizes search results.

    Args:
        model: FastAgent model specification (default: generic.mistral:7b)
        temperature: Sampling temperature 0.0-1.0 (default: 0.3)
        system_prompt: Custom system prompt. If None, uses default.

    Returns:
        FastAgent Agent instance configured for web search

    Raises:
        FastAgentError: If FastAgent is not initialized or agent creation fails

    Example:
        >>> websearch = create_websearch_agent()
        >>> # Agent will be registered as tool for orchestrator
    """
    if not FASTAGENT_AVAILABLE:
        raise FastAgentError("FastAgent not available")

    # Ensure FastAgent is initialized
    if "GENERIC_BASE_URL" not in os.environ:
        initialize_fastagent()

    # Default system prompt for web search
    if system_prompt is None:
        system_prompt = """You are a web search specialist for finding external information.

Your role is to:
1. Identify when external web search is needed
2. Formulate effective search queries
3. Use web search tools to find information
4. Summarize and validate search results
5. Cite external sources clearly

Always indicate when information comes from external sources vs. internal documents.
Be critical of web sources and prefer authoritative references."""

    try:
        agent = Agent(
            name="websearch",
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            tools=[]  # MCP web search tools will be added
        )
        logger.info(f"Created websearch agent with model {model}")
        return agent
    except Exception as e:
        raise FastAgentError(f"Failed to create websearch agent: {e}")


def get_agent_config(agent_type: str) -> Dict[str, Any]:
    """
    Get configuration for a specific agent type from config file.

    Args:
        agent_type: Type of agent (orchestrator, retrieval, analyst, websearch)

    Returns:
        Dictionary with agent configuration (model, temperature, etc.)

    Raises:
        FastAgentError: If agent type is unknown or config is missing

    Example:
        >>> config = get_agent_config("retrieval")
        >>> print(config["model"])
        generic.qwen2.5:latest
    """
    try:
        config = load_config(str(CONFIG_PATH))
    except Exception as e:
        logger.warning(f"Failed to load config: {e}. Using defaults.")
        config = {}

    # Default configurations
    defaults = {
        "orchestrator": {
            "model": "generic.llama3.2:latest",
            "temperature": 0.7,
        },
        "retrieval": {
            "model": "generic.qwen2.5:latest",
            "temperature": 0.5,
        },
        "analyst": {
            "model": "generic.llama3.2:latest",
            "temperature": 0.5,
        },
        "websearch": {
            "model": "generic.mistral:7b",
            "temperature": 0.3,
        }
    }

    if agent_type not in defaults:
        raise FastAgentError(
            f"Unknown agent type: {agent_type}. "
            f"Valid types: {', '.join(defaults.keys())}"
        )

    # Get from config or use defaults
    agent_config = config.get("agents", {}).get(agent_type, {})
    return {**defaults[agent_type], **agent_config}


def verify_ollama_models(required_models: Optional[list] = None) -> Dict[str, bool]:
    """
    Verify that required Ollama models are available.

    Args:
        required_models: List of model names to check. If None, checks all default models.

    Returns:
        Dictionary mapping model names to availability (True/False)

    Example:
        >>> models = verify_ollama_models()
        >>> if not all(models.values()):
        ...     print("Some models are missing!")
    """
    if required_models is None:
        required_models = [
            "llama3.2:latest",
            "qwen2.5:latest",
            "mistral:7b",
            "nomic-embed-text"
        ]

    try:
        import httpx
        base_url = os.environ.get("GENERIC_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        tags_url = base_url.replace("/v1", "/api/tags")

        response = httpx.get(tags_url, timeout=5.0)
        if response.status_code != 200:
            logger.error(f"Failed to fetch Ollama models: {response.status_code}")
            return {model: False for model in required_models}

        available_models = [m["name"] for m in response.json().get("models", [])]

        return {
            model: model in available_models
            for model in required_models
        }
    except Exception as e:
        logger.error(f"Error checking Ollama models: {e}")
        return {model: False for model in required_models}


# Convenience function for quick initialization
def setup_fastagent(verify_models: bool = True) -> bool:
    """
    One-step setup for FastAgent with Ollama.

    Initializes FastAgent, verifies Ollama connection, and optionally
    checks that required models are available.

    Args:
        verify_models: If True, verify all required models are pulled

    Returns:
        True if setup successful, False otherwise

    Example:
        >>> if setup_fastagent():
        ...     orchestrator = create_orchestrator_agent()
        ... else:
        ...     print("Setup failed - check Ollama is running")
    """
    try:
        initialize_fastagent(verify_connection=True)

        if verify_models:
            models = verify_ollama_models()
            missing = [m for m, available in models.items() if not available]
            if missing:
                logger.warning(
                    f"Missing Ollama models: {', '.join(missing)}. "
                    f"Run: ollama pull <model_name>"
                )
                return False

        logger.info("FastAgent setup complete")
        return True
    except Exception as e:
        logger.error(f"FastAgent setup failed: {e}")
        return False
