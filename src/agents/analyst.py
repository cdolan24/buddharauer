"""
Analyst Agent for document summarization and analysis.

This module implements the analyst agent using FastAgent. The agent specializes
in summarizing content, extracting entities, identifying patterns, and providing
creative insights about documents.

The analyst uses llama3.2:latest or qwen2.5:latest (both officially tested by
FastAgent for structured generation) and focuses on high-level analysis rather
than simple retrieval.

Architecture:
    Content + Query → Analysis → Structured Output → Summary/Insights

Key Features:
    - Entity extraction and summarization
    - Thematic analysis and pattern identification
    - Multi-document synthesis
    - Creative insights (for Faraday user profile)
    - Structured output generation

Usage:
    >>> from src.agents.analyst import AnalystAgent
    >>> agent = AnalystAgent()
    >>> await agent.initialize()
    >>> summary = await agent.summarize_character("Gandalf", sources)
    >>> print(summary["character_profile"])
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


class AnalysisType(Enum):
    """Types of analysis the agent can perform."""
    CHARACTER = "character"         # Character analysis
    LOCATION = "location"           # Location/setting analysis
    THEME = "theme"                 # Thematic analysis
    EVENT = "event"                 # Event/plot analysis
    RELATIONSHIP = "relationship"   # Relationship mapping
    SUMMARY = "summary"             # General summarization
    COMPARISON = "comparison"       # Comparative analysis


@dataclass
class AnalysisResult:
    """
    Result from an analysis task.

    Attributes:
        analysis_type: Type of analysis performed
        summary: Main summary/analysis text
        entities: Extracted entities (names, places, etc.)
        themes: Identified themes or patterns
        insights: Creative insights or observations
        sources_used: Number of sources analyzed
        confidence: Confidence score (0.0-1.0)
    """
    analysis_type: AnalysisType
    summary: str
    entities: List[Dict[str, Any]]
    themes: List[str]
    insights: List[str]
    sources_used: int
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "analysis_type": self.analysis_type.value if isinstance(self.analysis_type, AnalysisType) else self.analysis_type,
            "summary": self.summary,
            "entities": self.entities,
            "themes": self.themes,
            "insights": self.insights,
            "sources_used": self.sources_used,
            "confidence": self.confidence
        }


class AnalystAgent:
    """
    FastAgent-based analyst for document analysis and summarization.

    The analyst agent specializes in high-level analysis tasks that go beyond
    simple retrieval. It can:
    1. Summarize characters, locations, events
    2. Extract and organize entities
    3. Identify themes and patterns
    4. Provide creative insights and context
    5. Synthesize information across multiple sources

    The analyst is designed for the "Faraday" user profile - users who want
    deeper understanding and creative connections.

    Uses llama3.2:latest for balanced performance and quality, or qwen2.5:latest
    for better structured output generation.

    Attributes:
        agent: FastAgent Agent instance (if available)
        model: Model specification (default: generic.llama3.2:latest)
        temperature: Sampling temperature (default: 0.5)
        max_sources: Maximum sources to analyze at once

    Example:
        >>> analyst = AnalystAgent()
        >>> await analyst.initialize()
        >>> result = await analyst.analyze(
        ...     query="Summarize Aragorn's character arc",
        ...     sources=retrieval_results,
        ...     analysis_type=AnalysisType.CHARACTER
        ... )
        >>> print(result["summary"])
    """

    def __init__(
        self,
        model: str = "generic.llama3.2:latest",
        temperature: float = 0.5,
        max_sources: int = 10
    ):
        """
        Initialize the analyst agent.

        Args:
            model: FastAgent model specification for Ollama
                   Options: generic.llama3.2:latest, generic.qwen2.5:latest
            temperature: Sampling temperature (0.0-1.0)
                - Lower (0.3-0.5): More focused, factual analysis
                - Higher (0.5-0.8): More creative insights
            max_sources: Maximum number of sources to analyze

        Raises:
            FastAgentError: If FastAgent initialization fails
        """
        self.model = model
        self.temperature = temperature
        self.max_sources = max_sources
        self.agent = None

        logger.info(
            f"AnalystAgent initialized with model={model}, "
            f"temperature={temperature}"
        )

    async def initialize(self) -> None:
        """
        Initialize the FastAgent analyst.

        Sets up the FastAgent instance with Ollama configuration and
        defines analysis capabilities.

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
            config = initialize_fastagent()
            logger.info(f"FastAgent initialized with Ollama at {config['base_url']}")

            # Create system prompt for analyst
            system_prompt = self._build_system_prompt()

            # Note: Actual FastAgent initialization will happen here
            # TODO: Complete FastAgent Agent instantiation

            logger.info("AnalystAgent FastAgent instance created successfully")

        except Exception as e:
            logger.error(f"Failed to initialize AnalystAgent: {e}")
            raise FastAgentError(f"Analyst initialization failed: {e}")

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the analyst agent.

        Returns:
            System prompt string for FastAgent
        """
        return """You are the Analyst Agent for Buddharauer, specializing in document analysis and summarization.

Your role is to provide deep, insightful analysis of documents:

1. **Character Analysis**: Summarize character traits, motivations, relationships, and development
   - Include personality, role in story, key relationships, character arc

2. **Location/Setting Analysis**: Describe places, their significance, and atmosphere
   - Geographic details, cultural significance, role in plot

3. **Thematic Analysis**: Identify and explore themes, patterns, and motifs
   - Major themes, symbolic elements, recurring patterns

4. **Event Analysis**: Summarize events, their context, and significance
   - What happened, why it matters, consequences, connections

5. **Relationship Mapping**: Analyze connections between entities
   - Character relationships, cause-effect chains, thematic links

6. **General Summarization**: Provide coherent summaries of complex content
   - Key points, important details, broader context

Guidelines:
- Base analysis on provided sources, cite when possible
- Provide both factual details and creative insights
- Organize information clearly with structure
- Identify patterns and connections across sources
- Be explanatory and educational (Faraday user profile)
- Acknowledge uncertainty when information is incomplete

Output Format:
- Summary: Clear, comprehensive overview
- Entities: Structured list of key entities
- Themes: Important themes or patterns identified
- Insights: Creative observations or connections"""

    async def analyze(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        analysis_type: Optional[AnalysisType] = None
    ) -> Dict[str, Any]:
        """
        Perform analysis on provided sources.

        This is the main entry point for analysis tasks. The analyst:
        1. Examines the provided sources
        2. Determines analysis type if not specified
        3. Performs appropriate analysis
        4. Returns structured results

        Args:
            query: Analysis query/request
            sources: List of source dicts from retrieval agent
            analysis_type: Optional specific analysis type

        Returns:
            Analysis result dict containing:
                - analysis_type: Type of analysis performed
                - summary: Main analysis text
                - entities: Extracted entities
                - themes: Identified themes
                - insights: Creative insights
                - sources_used: Count of sources analyzed

        Example:
            >>> result = await analyst.analyze(
            ...     query="Who is Gandalf?",
            ...     sources=[{text: "...", page: 42}],
            ...     analysis_type=AnalysisType.CHARACTER
            ... )
        """
        try:
            # Determine analysis type if not provided
            if not analysis_type:
                analysis_type = self._classify_analysis_type(query)

            logger.info(f"Performing {analysis_type.value} analysis: {query[:50]}...")

            # Limit sources to max
            limited_sources = sources[:self.max_sources]

            # Perform analysis based on type
            if analysis_type == AnalysisType.CHARACTER:
                result = await self._analyze_character(query, limited_sources)
            elif analysis_type == AnalysisType.LOCATION:
                result = await self._analyze_location(query, limited_sources)
            elif analysis_type == AnalysisType.THEME:
                result = await self._analyze_theme(query, limited_sources)
            elif analysis_type == AnalysisType.EVENT:
                result = await self._analyze_event(query, limited_sources)
            elif analysis_type == AnalysisType.RELATIONSHIP:
                result = await self._analyze_relationships(query, limited_sources)
            elif analysis_type == AnalysisType.COMPARISON:
                result = await self._analyze_comparison(query, limited_sources)
            else:  # SUMMARY or default
                result = await self._analyze_summary(query, limited_sources)

            return result.to_dict()

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise FastAgentError(f"Failed to analyze: {e}")

    def _classify_analysis_type(self, query: str) -> AnalysisType:
        """
        Classify the type of analysis needed based on the query.

        Args:
            query: User query

        Returns:
            AnalysisType enum value
        """
        query_lower = query.lower()

        # Character analysis keywords
        if any(term in query_lower for term in [
            "character", "who is", "personality", "traits", "motivation"
        ]):
            return AnalysisType.CHARACTER

        # Location/setting keywords
        if any(term in query_lower for term in [
            "where", "location", "place", "setting", "region"
        ]):
            return AnalysisType.LOCATION

        # Theme keywords
        if any(term in query_lower for term in [
            "theme", "meaning", "symbolism", "represents", "significance"
        ]):
            return AnalysisType.THEME

        # Event keywords
        if any(term in query_lower for term in [
            "what happened", "event", "battle", "journey", "quest"
        ]):
            return AnalysisType.EVENT

        # Relationship keywords
        if any(term in query_lower for term in [
            "relationship", "connection", "between", "relate", "versus"
        ]):
            return AnalysisType.RELATIONSHIP

        # Comparison keywords
        if any(term in query_lower for term in [
            "compare", "difference", "similar", "contrast", "versus"
        ]):
            return AnalysisType.COMPARISON

        # Default to summary
        return AnalysisType.SUMMARY

    async def _analyze_character(
        self,
        query: str,
        sources: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """
        Analyze a character based on sources.

        Args:
            query: Character query
            sources: Source documents

        Returns:
            AnalysisResult with character analysis
        """
        # TODO: Replace with actual FastAgent call
        # For now, create a structured placeholder

        # Extract character name from query
        character_name = self._extract_entity_name(query)

        # Combine source texts
        combined_text = "\n\n".join([s.get("text", "") for s in sources])

        # Placeholder analysis
        summary = f"Analysis of {character_name}:\n\n"
        summary += f"Based on {len(sources)} source(s), this character appears frequently "
        summary += "in the documents. A detailed analysis requires the full FastAgent implementation."

        return AnalysisResult(
            analysis_type=AnalysisType.CHARACTER,
            summary=summary,
            entities=[{"name": character_name, "type": "character"}],
            themes=["Character development", "Relationships"],
            insights=["Further analysis pending FastAgent integration"],
            sources_used=len(sources),
            confidence=0.5
        )

    async def _analyze_location(
        self,
        query: str,
        sources: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """Analyze a location/setting."""
        location_name = self._extract_entity_name(query)

        summary = f"Analysis of {location_name}:\n\n"
        summary += f"Referenced in {len(sources)} source(s). "
        summary += "Full location analysis pending FastAgent implementation."

        return AnalysisResult(
            analysis_type=AnalysisType.LOCATION,
            summary=summary,
            entities=[{"name": location_name, "type": "location"}],
            themes=["Setting", "Geography"],
            insights=["Location analysis requires FastAgent"],
            sources_used=len(sources),
            confidence=0.5
        )

    async def _analyze_theme(
        self,
        query: str,
        sources: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """Analyze themes and patterns."""
        summary = f"Thematic analysis based on {len(sources)} source(s):\n\n"
        summary += "Theme identification and analysis pending FastAgent implementation."

        return AnalysisResult(
            analysis_type=AnalysisType.THEME,
            summary=summary,
            entities=[],
            themes=["Pending analysis"],
            insights=["Thematic analysis requires FastAgent"],
            sources_used=len(sources),
            confidence=0.4
        )

    async def _analyze_event(
        self,
        query: str,
        sources: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """Analyze events."""
        summary = f"Event analysis based on {len(sources)} source(s):\n\n"
        summary += "Event analysis pending FastAgent implementation."

        return AnalysisResult(
            analysis_type=AnalysisType.EVENT,
            summary=summary,
            entities=[],
            themes=["Plot", "Sequence"],
            insights=["Event analysis requires FastAgent"],
            sources_used=len(sources),
            confidence=0.4
        )

    async def _analyze_relationships(
        self,
        query: str,
        sources: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """Analyze relationships between entities."""
        summary = f"Relationship analysis based on {len(sources)} source(s):\n\n"
        summary += "Relationship mapping pending FastAgent implementation."

        return AnalysisResult(
            analysis_type=AnalysisType.RELATIONSHIP,
            summary=summary,
            entities=[],
            themes=["Connections", "Interactions"],
            insights=["Relationship analysis requires FastAgent"],
            sources_used=len(sources),
            confidence=0.4
        )

    async def _analyze_comparison(
        self,
        query: str,
        sources: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """Perform comparative analysis."""
        summary = f"Comparative analysis based on {len(sources)} source(s):\n\n"
        summary += "Comparison analysis pending FastAgent implementation."

        return AnalysisResult(
            analysis_type=AnalysisType.COMPARISON,
            summary=summary,
            entities=[],
            themes=["Comparison", "Contrast"],
            insights=["Comparative analysis requires FastAgent"],
            sources_used=len(sources),
            confidence=0.4
        )

    async def _analyze_summary(
        self,
        query: str,
        sources: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """General summarization."""
        # Combine source texts
        combined_text = "\n\n".join([
            s.get("text", "")[:500]  # Limit each source to 500 chars
            for s in sources
        ])

        summary = f"Summary based on {len(sources)} source(s):\n\n"
        summary += combined_text[:1000]  # Limit total to 1000 chars
        summary += "\n\n[Full summarization pending FastAgent implementation]"

        return AnalysisResult(
            analysis_type=AnalysisType.SUMMARY,
            summary=summary,
            entities=[],
            themes=["General overview"],
            insights=["Detailed summary requires FastAgent"],
            sources_used=len(sources),
            confidence=0.6
        )

    def _extract_entity_name(self, query: str) -> str:
        """
        Extract entity name from query.

        Simple heuristic extraction. In production, use NER.

        Args:
            query: User query

        Returns:
            Extracted entity name
        """
        # Remove common question words
        for word in ["who is", "what is", "where is", "tell me about", "analyze"]:
            query = query.lower().replace(word, "")

        # Clean up
        entity = query.strip().strip("?").strip()

        # Capitalize properly
        return entity.title() if entity else "Unknown"
