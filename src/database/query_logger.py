"""
Query logger for tracking user queries and system responses.

This module provides a SQLite-based logger to track:
    - User queries and questions
    - Agent responses and sources
    - Response times and performance metrics
    - User session information
    - Query success/failure rates

The logger enables:
    - Analytics on popular queries
    - Performance monitoring
    - User behavior analysis
    - System optimization insights
    - Debugging and troubleshooting

Database Schema:
    queries table:
        - id: INTEGER PRIMARY KEY AUTOINCREMENT
        - session_id: TEXT (unique session identifier)
        - user_id: TEXT (optional user identifier)
        - query: TEXT NOT NULL (user's question)
        - query_type: TEXT (question, summary, search, etc.)
        - response: TEXT (agent's response)
        - sources: TEXT (JSON array of source documents)
        - agent_used: TEXT (orchestrator, analyst, retrieval, web_search)
        - processing_time_ms: INTEGER (milliseconds)
        - success: INTEGER (1 for success, 0 for failure)
        - error_message: TEXT (if failed)
        - timestamp: TEXT (ISO format)
        - metadata: TEXT (JSON object with additional info)

Usage Example:
    >>> from src.database.query_logger import QueryLogger
    >>>
    >>> # Initialize logger
    >>> logger = QueryLogger("data_storage/queries.db")
    >>> await logger.initialize()
    >>>
    >>> # Log a query
    >>> query_id = await logger.log_query(
    ...     session_id="session_123",
    ...     query="Who is Aragorn?",
    ...     query_type="question",
    ...     user_id="faraday"
    ... )
    >>>
    >>> # Log response
    >>> await logger.log_response(
    ...     query_id=query_id,
    ...     response="Aragorn is a ranger...",
    ...     sources=[{"document_id": "doc_001", "page": 42}],
    ...     agent_used="orchestrator",
    ...     processing_time_ms=1234,
    ...     success=True
    ... )
    >>>
    >>> # Get analytics
    >>> stats = await logger.get_statistics()
    >>> print(f"Total queries: {stats['total_queries']}")

See Also:
    - DocumentRegistry: For document tracking
    - VectorStore: For vector database operations
"""

import sqlite3
import aiosqlite
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for query types
QueryType = Literal["question", "summary", "search", "analysis", "web_search", "other"]


@dataclass
class QueryRecord:
    """
    A query record in the logger.

    Attributes:
        id: Auto-incrementing query ID
        session_id: Unique session identifier
        user_id: Optional user identifier
        query: User's question or request
        query_type: Type of query
        response: Agent's response
        sources: JSON string of source documents
        agent_used: Which agent handled the query
        processing_time_ms: Response time in milliseconds
        success: Whether query succeeded (1) or failed (0)
        error_message: Error message if failed
        timestamp: When query was made
        metadata: Additional metadata as JSON string
    """
    id: int
    session_id: str
    user_id: Optional[str]
    query: str
    query_type: str
    response: Optional[str]
    sources: Optional[str]  # JSON string
    agent_used: Optional[str]
    processing_time_ms: Optional[int]
    success: Optional[int]
    error_message: Optional[str]
    timestamp: str
    metadata: Optional[str]  # JSON string

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryRecord":
        """Create a QueryRecord from a dictionary."""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, parsing JSON fields."""
        data = asdict(self)
        # Parse JSON strings back to objects
        if data.get("sources"):
            try:
                data["sources"] = json.loads(data["sources"])
            except (json.JSONDecodeError, TypeError):
                pass
        if data.get("metadata"):
            try:
                data["metadata"] = json.loads(data["metadata"])
            except (json.JSONDecodeError, TypeError):
                pass
        return data


class QueryLogger:
    """
    SQLite-based logger for tracking user queries and responses.

    Provides logging and analytics for query performance and user behavior.
    """

    def __init__(self, db_path: str | Path = "data_storage/queries.db"):
        """
        Initialize the query logger.

        Args:
            db_path: Path to SQLite database file

        Example:
            >>> logger = QueryLogger("./queries.db")
            >>> await logger.initialize()
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """
        Initialize the database schema.

        Creates the queries table if it doesn't exist.
        Should be called once during application startup.

        Example:
            >>> logger = QueryLogger()
            >>> await logger.initialize()
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    query TEXT NOT NULL,
                    query_type TEXT,
                    response TEXT,
                    sources TEXT,
                    agent_used TEXT,
                    processing_time_ms INTEGER,
                    success INTEGER,
                    error_message TEXT,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            # Create indexes for common queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_session
                ON queries(session_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_user
                ON queries(user_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON queries(timestamp)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_type
                ON queries(query_type)
            """)

            await db.commit()
            logger.info(f"Query logger initialized at {self.db_path}")

    async def log_query(
        self,
        session_id: str,
        query: str,
        query_type: Optional[QueryType] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log a new query.

        Args:
            session_id: Unique session identifier
            query: User's question or request
            query_type: Type of query (question, summary, etc.)
            user_id: Optional user identifier
            metadata: Additional metadata dictionary

        Returns:
            Query ID (auto-incremented)

        Example:
            >>> query_id = await logger.log_query(
            ...     session_id="session_123",
            ...     query="Who is Aragorn?",
            ...     query_type="question",
            ...     user_id="faraday"
            ... )
        """
        now = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO queries (
                    session_id, user_id, query, query_type, timestamp, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_id,
                query,
                query_type or "other",
                now,
                metadata_json
            ))
            await db.commit()
            query_id = cursor.lastrowid

        logger.debug(f"Logged query {query_id} from session {session_id}")
        return query_id

    async def log_response(
        self,
        query_id: int,
        response: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        agent_used: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Log the response for a query.

        Args:
            query_id: ID of the original query
            response: Agent's response text
            sources: List of source documents with metadata
            agent_used: Which agent handled the query
            processing_time_ms: Response time in milliseconds
            success: Whether the query succeeded
            error_message: Error message if failed

        Example:
            >>> await logger.log_response(
            ...     query_id=123,
            ...     response="Aragorn is a ranger...",
            ...     sources=[{"document_id": "doc_001", "page": 42}],
            ...     agent_used="orchestrator",
            ...     processing_time_ms=1234,
            ...     success=True
            ... )
        """
        sources_json = json.dumps(sources) if sources else None

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE queries
                SET response = ?,
                    sources = ?,
                    agent_used = ?,
                    processing_time_ms = ?,
                    success = ?,
                    error_message = ?
                WHERE id = ?
            """, (
                response,
                sources_json,
                agent_used,
                processing_time_ms,
                1 if success else 0,
                error_message,
                query_id
            ))
            await db.commit()

        logger.debug(f"Logged response for query {query_id}")

    async def get_by_id(self, query_id: int) -> Optional[QueryRecord]:
        """
        Get a query by ID.

        Args:
            query_id: Query ID

        Returns:
            QueryRecord if found, None otherwise

        Example:
            >>> record = await logger.get_by_id(123)
            >>> if record:
            ...     print(f"Query: {record.query}")
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM queries WHERE id = ?", (query_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return QueryRecord.from_dict(dict(row))
                return None

    async def get_by_session(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[QueryRecord]:
        """
        Get all queries for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of queries to return

        Returns:
            List of queries ordered by timestamp (newest first)

        Example:
            >>> history = await logger.get_by_session("session_123")
            >>> for record in history:
            ...     print(f"{record.query} -> {record.response}")
        """
        query = "SELECT * FROM queries WHERE session_id = ? ORDER BY timestamp DESC"
        params = [session_id]

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [QueryRecord.from_dict(dict(row)) for row in rows]

    async def get_popular_queries(
        self,
        limit: int = 10,
        days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get most popular queries.

        Args:
            limit: Number of queries to return
            days: Limit to queries from last N days (None for all time)

        Returns:
            List of dictionaries with query text and count

        Example:
            >>> popular = await logger.get_popular_queries(limit=5, days=7)
            >>> for item in popular:
            ...     print(f"{item['query']}: {item['count']} times")
        """
        query = """
            SELECT query, COUNT(*) as count
            FROM queries
        """

        params = []
        if days is not None:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            query += " WHERE timestamp >= ?"
            params.append(cutoff)

        query += " GROUP BY LOWER(query) ORDER BY count DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [{"query": row[0], "count": row[1]} for row in rows]

    async def get_statistics(
        self,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get overall query statistics.

        Args:
            days: Limit to last N days (None for all time)

        Returns:
            Dictionary with statistics including:
                - total_queries: Total number of queries
                - successful_queries: Number of successful queries
                - failed_queries: Number of failed queries
                - success_rate: Percentage of successful queries
                - avg_response_time_ms: Average response time
                - queries_by_type: Count by query type
                - queries_by_agent: Count by agent

        Example:
            >>> stats = await logger.get_statistics(days=7)
            >>> print(f"Success rate: {stats['success_rate']:.1f}%")
            >>> print(f"Avg response time: {stats['avg_response_time_ms']}ms")
        """
        where_clause = ""
        params = []

        if days is not None:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            where_clause = " WHERE timestamp >= ?"
            params.append(cutoff)

        async with aiosqlite.connect(self.db_path) as db:
            # Get total counts
            async with db.execute(
                f"SELECT COUNT(*) FROM queries{where_clause}", params
            ) as cursor:
                total = (await cursor.fetchone())[0]

            # Get success/failure counts
            async with db.execute(
                f"SELECT success, COUNT(*) FROM queries{where_clause} GROUP BY success",
                params
            ) as cursor:
                success_rows = await cursor.fetchall()
                successful = sum(count for success, count in success_rows if success == 1)
                failed = sum(count for success, count in success_rows if success == 0)

            # Calculate success rate
            success_rate = (successful / total * 100) if total > 0 else 0.0

            # Get average response time
            async with db.execute(
                f"""
                SELECT AVG(processing_time_ms)
                FROM queries
                {where_clause} AND processing_time_ms IS NOT NULL
                """,
                params
            ) as cursor:
                avg_time = (await cursor.fetchone())[0] or 0.0

            # Get counts by type
            async with db.execute(
                f"""
                SELECT query_type, COUNT(*) as count
                FROM queries{where_clause}
                GROUP BY query_type
                """,
                params
            ) as cursor:
                type_rows = await cursor.fetchall()
                queries_by_type = {row[0]: row[1] for row in type_rows}

            # Get counts by agent
            async with db.execute(
                f"""
                SELECT agent_used, COUNT(*) as count
                FROM queries
                {where_clause} AND agent_used IS NOT NULL
                GROUP BY agent_used
                """,
                params
            ) as cursor:
                agent_rows = await cursor.fetchall()
                queries_by_agent = {row[0]: row[1] for row in agent_rows}

            return {
                "total_queries": total,
                "successful_queries": successful,
                "failed_queries": failed,
                "success_rate": success_rate,
                "avg_response_time_ms": avg_time,
                "queries_by_type": queries_by_type,
                "queries_by_agent": queries_by_agent
            }

    async def delete_old_queries(self, days: int = 90):
        """
        Delete queries older than specified days.

        Args:
            days: Delete queries older than this many days

        Returns:
            Number of queries deleted

        Example:
            >>> # Delete queries older than 90 days
            >>> deleted = await logger.delete_old_queries(90)
            >>> print(f"Deleted {deleted} old queries")
        """
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM queries WHERE timestamp < ?", (cutoff,)
            )
            await db.commit()
            deleted = cursor.rowcount

        logger.info(f"Deleted {deleted} queries older than {days} days")
        return deleted

    async def clear_session(self, session_id: str):
        """
        Clear all queries for a session.

        Args:
            session_id: Session identifier

        Example:
            >>> await logger.clear_session("session_123")
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM queries WHERE session_id = ?", (session_id,)
            )
            await db.commit()

        logger.info(f"Cleared queries for session {session_id}")
