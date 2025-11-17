"""
Document registry for tracking processed PDFs and their metadata.

This module provides a SQLite-based registry to track:
    - Document processing status (pending, processing, completed, failed)
    - Document metadata (filename, pages, size, upload date)
    - Processing timestamps and statistics
    - Chunk and token counts
    - Error information for failed documents

The registry enables:
    - Preventing duplicate processing
    - Tracking document lifecycle
    - Querying document status and history
    - Cleanup and maintenance operations

Database Schema:
    documents table:
        - id: TEXT PRIMARY KEY (hash of file content)
        - filename: TEXT NOT NULL
        - filepath: TEXT NOT NULL
        - status: TEXT NOT NULL (pending, processing, completed, failed)
        - pages: INTEGER
        - file_size_bytes: INTEGER
        - upload_date: TEXT (ISO format)
        - processing_start: TEXT (ISO format)
        - processing_end: TEXT (ISO format)
        - processing_time_seconds: REAL
        - chunk_count: INTEGER
        - token_count: INTEGER
        - error_message: TEXT
        - created_at: TEXT (ISO format)
        - updated_at: TEXT (ISO format)

Usage Example:
    >>> from src.database.document_registry import DocumentRegistry
    >>> from pathlib import Path
    >>>
    >>> # Initialize registry
    >>> registry = DocumentRegistry("data_storage/documents.db")
    >>>
    >>> # Add document
    >>> doc_id = await registry.add_document(
    ...     filepath=Path("data/sample.pdf"),
    ...     filename="sample.pdf",
    ...     file_size=1024000,
    ...     pages=42
    ... )
    >>>
    >>> # Update status
    >>> await registry.update_status(doc_id, "processing")
    >>>
    >>> # Mark as completed
    >>> await registry.mark_completed(doc_id, chunk_count=150, token_count=5000)
    >>>
    >>> # Query documents
    >>> completed = await registry.get_by_status("completed")
    >>> print(f"Processed {len(completed)} documents")

See Also:
    - VectorStore: For vector database operations
    - PipelineOrchestrator: For document processing workflow
"""

import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import aiosqlite

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for document status
DocumentStatus = Literal["pending", "processing", "completed", "failed"]


@dataclass
class DocumentRecord:
    """
    A document record in the registry.

    Attributes:
        id: Unique identifier (hash of file content)
        filename: Original filename
        filepath: Full path to the file
        status: Processing status
        pages: Number of pages in PDF
        file_size_bytes: File size in bytes
        upload_date: When document was added to registry
        processing_start: When processing began
        processing_end: When processing completed
        processing_time_seconds: Total processing time
        chunk_count: Number of chunks created
        token_count: Total token count
        error_message: Error message if failed
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """
    id: str
    filename: str
    filepath: str
    status: DocumentStatus
    pages: Optional[int] = None
    file_size_bytes: Optional[int] = None
    upload_date: Optional[str] = None
    processing_start: Optional[str] = None
    processing_end: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    chunk_count: Optional[int] = None
    token_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentRecord":
        """Create a DocumentRecord from a dictionary."""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class DocumentRegistry:
    """
    SQLite-based registry for tracking document processing.

    Provides CRUD operations and queries for document metadata and status.
    """

    def __init__(self, db_path: str | Path = "data_storage/documents.db"):
        """
        Initialize the document registry.

        Args:
            db_path: Path to SQLite database file

        Example:
            >>> registry = DocumentRegistry("./my_documents.db")
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """
        Initialize the database schema.

        Creates the documents table if it doesn't exist.
        Should be called once during application startup.

        Example:
            >>> registry = DocumentRegistry()
            >>> await registry.initialize()
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pages INTEGER,
                    file_size_bytes INTEGER,
                    upload_date TEXT,
                    processing_start TEXT,
                    processing_end TEXT,
                    processing_time_seconds REAL,
                    chunk_count INTEGER,
                    token_count INTEGER,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Create indexes for common queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_status
                ON documents(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_filename
                ON documents(filename)
            """)

            await db.commit()
            logger.info(f"Document registry initialized at {self.db_path}")

    @staticmethod
    def compute_file_hash(filepath: Path) -> str:
        """
        Compute SHA256 hash of file content for unique ID.

        Args:
            filepath: Path to file

        Returns:
            Hexadecimal hash string

        Example:
            >>> file_id = DocumentRegistry.compute_file_hash(Path("test.pdf"))
            >>> print(f"File ID: {file_id}")
        """
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    async def add_document(
        self,
        filepath: Path,
        filename: str,
        file_size: int,
        pages: Optional[int] = None
    ) -> str:
        """
        Add a new document to the registry.

        Args:
            filepath: Full path to document
            filename: Original filename
            file_size: File size in bytes
            pages: Number of pages (optional)

        Returns:
            Document ID (file hash)

        Raises:
            ValueError: If document already exists

        Example:
            >>> doc_id = await registry.add_document(
            ...     filepath=Path("data/sample.pdf"),
            ...     filename="sample.pdf",
            ...     file_size=1024000,
            ...     pages=42
            ... )
        """
        # Compute unique ID based on file content
        doc_id = self.compute_file_hash(filepath)

        # Check if already exists
        existing = await self.get_by_id(doc_id)
        if existing:
            raise ValueError(f"Document {filename} already exists with ID {doc_id}")

        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO documents (
                    id, filename, filepath, status, pages, file_size_bytes,
                    upload_date, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                filename,
                str(filepath),
                "pending",
                pages,
                file_size,
                now,
                now,
                now
            ))
            await db.commit()

        logger.info(f"Added document {filename} with ID {doc_id[:8]}...")
        return doc_id

    async def get_by_id(self, doc_id: str) -> Optional[DocumentRecord]:
        """
        Get document by ID.

        Args:
            doc_id: Document ID

        Returns:
            DocumentRecord if found, None otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM documents WHERE id = ?", (doc_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return DocumentRecord.from_dict(dict(row))
                return None

    async def get_by_status(self, status: DocumentStatus) -> List[DocumentRecord]:
        """
        Get all documents with a specific status.

        Args:
            status: Status to filter by

        Returns:
            List of matching documents

        Example:
            >>> completed = await registry.get_by_status("completed")
            >>> print(f"Found {len(completed)} completed documents")
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM documents WHERE status = ? ORDER BY created_at DESC",
                (status,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [DocumentRecord.from_dict(dict(row)) for row in rows]

    async def list_all(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[DocumentRecord]:
        """
        List all documents with optional pagination.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of documents ordered by creation date (newest first)

        Example:
            >>> # Get first page (20 docs)
            >>> page1 = await registry.list_all(limit=20, offset=0)
            >>> # Get second page
            >>> page2 = await registry.list_all(limit=20, offset=20)
        """
        query = "SELECT * FROM documents ORDER BY created_at DESC"
        params = []

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params = [limit, offset]

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [DocumentRecord.from_dict(dict(row)) for row in rows]

    async def count_by_status(self) -> Dict[str, int]:
        """
        Get count of documents by status.

        Returns:
            Dictionary mapping status to count

        Example:
            >>> counts = await registry.count_by_status()
            >>> print(f"Pending: {counts.get('pending', 0)}")
            >>> print(f"Completed: {counts.get('completed', 0)}")
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT status, COUNT(*) as count FROM documents GROUP BY status"
            ) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}

    async def update_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        error_message: Optional[str] = None
    ):
        """
        Update document status.

        Args:
            doc_id: Document ID
            status: New status
            error_message: Error message if status is "failed"

        Example:
            >>> await registry.update_status(doc_id, "processing")
            >>> # Later, if processing fails:
            >>> await registry.update_status(
            ...     doc_id, "failed", error_message="PDF corrupted"
            ... )
        """
        now = datetime.now(timezone.utc).isoformat()

        # Set processing_start when status changes to processing
        processing_start = None
        if status == "processing":
            processing_start = now

        async with aiosqlite.connect(self.db_path) as db:
            if status == "processing":
                await db.execute("""
                    UPDATE documents
                    SET status = ?, processing_start = ?, updated_at = ?
                    WHERE id = ?
                """, (status, processing_start, now, doc_id))
            elif error_message:
                await db.execute("""
                    UPDATE documents
                    SET status = ?, error_message = ?, updated_at = ?
                    WHERE id = ?
                """, (status, error_message, now, doc_id))
            else:
                await db.execute("""
                    UPDATE documents
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                """, (status, now, doc_id))

            await db.commit()

    async def mark_completed(
        self,
        doc_id: str,
        chunk_count: int,
        token_count: int
    ):
        """
        Mark document as completed with processing statistics.

        Args:
            doc_id: Document ID
            chunk_count: Number of chunks created
            token_count: Total token count

        Example:
            >>> await registry.mark_completed(doc_id, chunk_count=150, token_count=5000)
        """
        now = datetime.now(timezone.utc).isoformat()

        # Get processing start time to calculate duration
        doc = await self.get_by_id(doc_id)
        processing_time = None
        if doc and doc.processing_start:
            start = datetime.fromisoformat(doc.processing_start)
            end = datetime.now(timezone.utc)
            processing_time = (end - start).total_seconds()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE documents
                SET status = ?,
                    processing_end = ?,
                    processing_time_seconds = ?,
                    chunk_count = ?,
                    token_count = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                "completed",
                now,
                processing_time,
                chunk_count,
                token_count,
                now,
                doc_id
            ))
            await db.commit()

        logger.info(
            f"Marked document {doc_id[:8]}... as completed "
            f"({chunk_count} chunks, {token_count} tokens)"
        )

    async def delete_document(self, doc_id: str):
        """
        Delete a document from the registry.

        Args:
            doc_id: Document ID

        Warning:
            This only removes the registry entry, not the actual file
            or vector store entries.

        Example:
            >>> await registry.delete_document(doc_id)
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            await db.commit()

        logger.info(f"Deleted document {doc_id[:8]}... from registry")

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall registry statistics.

        Returns:
            Dictionary with statistics including:
                - total_documents: Total number of documents
                - status_counts: Count by status
                - total_chunks: Sum of all chunks
                - total_tokens: Sum of all tokens
                - avg_processing_time: Average processing time in seconds

        Example:
            >>> stats = await registry.get_statistics()
            >>> print(f"Total documents: {stats['total_documents']}")
            >>> print(f"Average processing time: {stats['avg_processing_time']:.2f}s")
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Get total count
            async with db.execute("SELECT COUNT(*) FROM documents") as cursor:
                total = (await cursor.fetchone())[0]

            # Get status counts
            status_counts = await self.count_by_status()

            # Get aggregate stats
            async with db.execute("""
                SELECT
                    SUM(chunk_count) as total_chunks,
                    SUM(token_count) as total_tokens,
                    AVG(processing_time_seconds) as avg_time
                FROM documents
                WHERE status = 'completed'
            """) as cursor:
                row = await cursor.fetchone()
                total_chunks = row[0] or 0
                total_tokens = row[1] or 0
                avg_time = row[2] or 0.0

            return {
                "total_documents": total,
                "status_counts": status_counts,
                "total_chunks": total_chunks,
                "total_tokens": total_tokens,
                "avg_processing_time": avg_time
            }
