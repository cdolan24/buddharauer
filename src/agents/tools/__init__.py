"""
MCP Tools for FastAgent Agents.

This module contains tool definitions for use with FastAgent agents.
Tools provide interfaces to external systems and services:

- Vector DB tools: Search and retrieve from vector database
- Web search tools: External web search via MCP servers
- Document tools: Access and process documents

Usage:
    >>> from src.agents.tools import create_vector_search_tool
    >>> tool = create_vector_search_tool(vector_store)
    >>> # Register tool with FastAgent agent
"""

from .vector_db_tools import create_vector_search_tool, create_chunk_context_tool
from .web_search_tools import create_duckduckgo_tool, create_brave_search_tool

__all__ = [
    "create_vector_search_tool",
    "create_chunk_context_tool",
    "create_duckduckgo_tool",
    "create_brave_search_tool",
]
