"""
Pipeline orchestrator for processing PDFs into the vector store.

This module provides the main orchestration layer for the document processing
pipeline. It coordinates PDF extraction, chunking, embedding generation, and
vector storage while providing resilient error recovery and comprehensive
monitoring.

Key Features:
    - Batch processing of multiple PDFs
    - Automatic retry with exponential backoff
    - State persistence for recovery from failures
    - Comprehensive metrics and monitoring
    - Duplicate detection to avoid reprocessing

Usage Example:
    >>> from pathlib import Path
    >>> from src.pipeline.chunker import ChunkPipeline, SemanticChunker
    >>> from src.database.vector_store import VectorStore
    >>>
    >>> # Initialize components
    >>> chunker = SemanticChunker(chunk_size=800, chunk_overlap=150)
    >>> chunk_pipeline = ChunkPipeline(chunker)
    >>> vector_store = VectorStore("./vector_db")
    >>>
    >>> # Create orchestrator
    >>> orchestrator = PipelineOrchestrator(
    ...     chunk_pipeline=chunk_pipeline,
    ...     vector_store=vector_store,
    ...     batch_size=32
    ... )
    >>>
    >>> # Process a directory of PDFs
    >>> import asyncio
    >>> stats = asyncio.run(orchestrator.process_directory(Path("data")))
    >>> print(f"Processed {stats.successful_files}/{stats.total_files} files")
    >>> print(f"Total chunks: {stats.total_chunks}")

Error Recovery:
    The orchestrator implements comprehensive error recovery:
    - Failed operations are automatically retried (up to 3 times)
    - State is persisted to disk for crash recovery
    - Duplicate processing is prevented
    - Failed files don't block processing of other files

Monitoring:
    All operations are tracked with detailed metrics:
    - Processing time per file
    - Chunk and token counts
    - Success/failure rates
    - Retry statistics

See Also:
    - ChunkPipeline: For PDF chunking configuration
    - VectorStore: For vector database operations
    - RecoveryManager: For state persistence details
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import asyncio
import time
from datetime import datetime

from src.pipeline.chunker import ChunkPipeline, TextChunk
from src.database.vector_store import VectorStore
from src.utils.logging import get_logger
from src.pipeline.recovery import RecoveryManager, with_retry
from src.pipeline.monitoring import monitor, Metric, MetricType

logger = get_logger(__name__)


@dataclass
class ProcessingStats:
    """Statistics for document processing."""
    total_files: int
    successful_files: int
    failed_files: int
    total_chunks: int
    total_tokens: int
    processing_time: float
    errors: Dict[str, str]  # file -> error message
    retry_successes: int    # Files that succeeded after retries
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary for persistence."""
        return {
            'total_files': self.total_files,
            'successful_files': self.successful_files,
            'failed_files': self.failed_files,
            'total_chunks': self.total_chunks,
            'total_tokens': self.total_tokens,
            'processing_time': self.processing_time,
            'errors': self.errors,
            'retry_successes': self.retry_successes
        }
        
    def update_metrics(self) -> None:
        """Update monitoring metrics with current stats."""
        metrics = [
            Metric("pipeline_total_files", self.total_files, MetricType.GAUGE),
            Metric("pipeline_successful_files", self.successful_files, MetricType.COUNTER),
            Metric("pipeline_failed_files", self.failed_files, MetricType.COUNTER),
            Metric("pipeline_total_chunks", self.total_chunks, MetricType.COUNTER),
            Metric("pipeline_total_tokens", self.total_tokens, MetricType.COUNTER),
            Metric("pipeline_processing_time", self.processing_time, MetricType.GAUGE),
            Metric("pipeline_retry_successes", self.retry_successes, MetricType.COUNTER),
            Metric(
                "pipeline_success_rate",
                self.successful_files / max(self.total_files, 1),
                MetricType.GAUGE
            )
        ]
        
        for metric in metrics:
            monitor.record_metric(metric)


class PipelineOrchestrator:
    """Orchestrates the document processing pipeline with resilient error recovery."""
    
    def __init__(self,
                 chunk_pipeline: ChunkPipeline,
                 vector_store: VectorStore,
                 batch_size: int = 32,
                 state_dir: Optional[Path] = None):
        """
        Initialize the orchestrator.
        
        Args:
            chunk_pipeline: Pipeline for processing PDFs into chunks
            vector_store: Vector store for saving embeddings
            batch_size: Number of chunks to process at once
            state_dir: Directory for storing recovery state
        """
        self.chunk_pipeline = chunk_pipeline
        self.vector_store = vector_store
        self.batch_size = batch_size
        self.stats = ProcessingStats(0, 0, 0, 0, 0, 0.0, {}, 0)
        
        # Initialize recovery manager
        if state_dir is None:
            state_dir = Path("data/recovery")
        self.recovery = RecoveryManager(state_dir)
        
        # Track processed files to avoid duplicates
        self.processed_files: Set[str] = set()
        
    @with_retry(max_retries=3, initial_delay=1.0)
    async def _add_to_vector_store(
        self,
        texts: List[str],
        metadata_list: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add documents to vector store with retry logic.
        
        Args:
            texts: List of text chunks
            metadata_list: List of metadata dictionaries
            
        Returns:
            List of document IDs
        """
        return await self.vector_store.add_documents(
            texts=texts,
            metadata_list=metadata_list,
            batch_size=self.batch_size
        )
        
    async def process_pdf(self, pdf_path: Path) -> bool:
        """
        Process a single PDF file with error recovery.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            bool: True if processing was successful
        """
        pdf_str = str(pdf_path)
        if pdf_str in self.processed_files:
            logger.info(f"Skipping already processed file: {pdf_path}")
            return True
            
        # Start tracking operation
        recovery_state = self.recovery.start_operation(
            "process_pdf",
            {"pdf_path": pdf_str}
        )
        
        # Start monitoring
        start_time = time.time()
        labels = {"file": pdf_str}
        
        try:
            # Get chunks from the document
            with monitor.track_operation_time("chunk_extraction", labels):
                chunks = self.chunk_pipeline.process_file(pdf_path)
            
            if not chunks:
                raise ValueError("No chunks extracted from document")
                
            # Record chunking metrics
            monitor.record_metric(Metric(
                "pdf_chunk_count",
                len(chunks),
                MetricType.HISTOGRAM,
                labels=labels
            ))
                
            # Prepare batch data
            texts = [chunk.text for chunk in chunks]
            metadata = [
                {**chunk.metadata, "source_file": pdf_str}
                for chunk in chunks
            ]
            
            # Add to vector store with retries
            with monitor.track_operation_time("vector_store_insert", labels):
                doc_ids = await self._add_to_vector_store(texts, metadata)
            
            # Update stats
            self.stats.successful_files += 1
            self.stats.total_chunks += len(chunks)
            # Estimate tokens (rough approximation)
            token_count = sum(len(text.split()) * 1.3 for text in texts)
            self.stats.total_tokens += token_count
            
            # Record token metrics
            monitor.record_metric(Metric(
                "pdf_token_count",
                token_count,
                MetricType.HISTOGRAM,
                labels=labels
            ))
            
            # Mark as processed
            self.processed_files.add(pdf_str)
            
            # Update recovery state
            self.recovery.update_operation(
                recovery_state.operation_id,
                "completed"
            )
            
            # Record processing time
            processing_time = time.time() - start_time
            monitor.record_metric(Metric(
                "pdf_processing_time",
                processing_time,
                MetricType.HISTOGRAM,
                labels=labels
            ))
            
            # Update overall stats metrics
            self.stats.update_metrics()
            
            logger.info(
                f"Successfully processed {pdf_path} - "
                f"{len(chunks)} chunks, {int(token_count)} tokens, "
                f"{processing_time:.2f}s"
            )
            return True
            
        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"Failed to process {pdf_path}: {str(e)}")
            self.stats.failed_files += 1
            self.stats.errors[pdf_str] = str(e)
            
            # Record error metrics
            monitor.record_metric(Metric(
                "pdf_processing_errors",
                1,
                MetricType.COUNTER,
                labels={**labels, "error": str(e)}
            ))
            
            monitor.record_metric(Metric(
                "pdf_error_processing_time",
                error_time,
                MetricType.HISTOGRAM,
                labels=labels
            ))
            
            # Update recovery state
            self.recovery.update_operation(
                recovery_state.operation_id,
                "failed",
                str(e)
            )
            
            # Update overall stats metrics
            self.stats.update_metrics()
            
            return False
            
    async def process_directory(self, 
                              dir_path: Path,
                              recursive: bool = True) -> ProcessingStats:
        """
        Process all PDFs in a directory with automatic recovery.
        
        Args:
            dir_path: Directory containing PDFs
            recursive: Whether to process subdirectories
            
        Returns:
            Processing statistics
        """
        start_time = time.time()
        pattern = "**/*.pdf" if recursive else "*.pdf"
        labels = {"directory": str(dir_path), "recursive": str(recursive)}
        
        # Record start of processing
        monitor.record_metric(Metric(
            "directory_processing_start",
            time.time(),
            MetricType.GAUGE,
            labels=labels
        ))
        
        # Check for incomplete operations from previous runs
        incomplete = self.recovery.list_incomplete_operations()
        if incomplete:
            monitor.record_metric(Metric(
                "incomplete_operations",
                len(incomplete),
                MetricType.GAUGE,
                labels=labels
            ))
            
            logger.info(f"Found {len(incomplete)} incomplete operations")
            for op_id, state in incomplete.items():
                if state.operation_type == "process_pdf":
                    pdf_path = Path(state.input_data["pdf_path"])
                    if pdf_path.exists():
                        logger.info(f"Retrying incomplete operation: {pdf_path}")
                        if await self.process_pdf(pdf_path):
                            self.stats.retry_successes += 1
        
        # Process new files
        pdf_files = list(dir_path.glob(pattern))
        self.stats.total_files = len(pdf_files)
        
        # Initialize progress tracking
        monitor.update_progress(
            operation="process_directory",
            completed=0,
            total=len(pdf_files),
            current_item=str(dir_path),
            error_count=0
        )
        
        # Record directory metrics
        monitor.record_metric(Metric(
            "directory_pdf_count",
            len(pdf_files),
            MetricType.GAUGE,
            labels=labels
        ))
        
        # Process files with progress tracking
        for i, pdf_path in enumerate(pdf_files, 1):
            success = await self.process_pdf(pdf_path)
            monitor.update_progress(
                operation="process_directory",
                completed=i,
                total=len(pdf_files),
                current_item=str(pdf_path),
                error_count=self.stats.failed_files
            )
            
        processing_time = time.time() - start_time
        self.stats.processing_time = processing_time
        
        # Record completion metrics
        monitor.record_metric(Metric(
            "directory_processing_time",
            processing_time,
            MetricType.HISTOGRAM,
            labels=labels
        ))
        
        monitor.record_metric(Metric(
            "directory_processing_complete",
            time.time(),
            MetricType.GAUGE,
            labels={
                **labels,
                "success_rate": f"{self.stats.successful_files/self.stats.total_files:.2%}",
                "duration": f"{processing_time:.1f}s"
            }
        ))
        
        # Log summary
        logger.info(
            f"Processed {self.stats.successful_files}/{self.stats.total_files} files "
            f"({self.stats.total_chunks} chunks) in {self.stats.processing_time:.1f}s"
        )
        
        if self.stats.retry_successes:
            logger.info(f"Successfully recovered {self.stats.retry_successes} files")
            
        if self.stats.failed_files:
            logger.warning(f"Failed to process {self.stats.failed_files} files")
        
        # Update final stats metrics
        self.stats.update_metrics()
        return self.stats
        
    def get_stats(self) -> ProcessingStats:
        """Get current processing statistics."""
        return self.stats