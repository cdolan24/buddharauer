"""
Pipeline orchestrator for processing PDFs into the vector store.
Handles document processing, chunking, and vector storage with error recovery.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
import time
from datetime import datetime

from src.pipeline.chunker import ChunkPipeline, TextChunk
from src.database.vector_store import VectorStore
from src.utils.logging import get_logger

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


class PipelineOrchestrator:
    """Orchestrates the document processing pipeline."""
    
    def __init__(self,
                 chunk_pipeline: ChunkPipeline,
                 vector_store: VectorStore,
                 batch_size: int = 32):
        """
        Initialize the orchestrator.
        
        Args:
            chunk_pipeline: Pipeline for processing PDFs into chunks
            vector_store: Vector store for saving embeddings
            batch_size: Number of chunks to process at once
        """
        self.chunk_pipeline = chunk_pipeline
        self.vector_store = vector_store
        self.batch_size = batch_size
        self.stats = ProcessingStats(0, 0, 0, 0, 0, 0.0, {})
        
    async def process_pdf(self, pdf_path: Path) -> bool:
        """
        Process a single PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            bool: True if processing was successful
        """
        try:
            # Get chunks from the document
            chunks = self.chunk_pipeline.process_file(pdf_path)
            
            if not chunks:
                raise ValueError("No chunks extracted from document")
                
            # Prepare batch data
            texts = [chunk.text for chunk in chunks]
            metadata = [chunk.metadata for chunk in chunks]
            
            # Add to vector store with batching
            doc_ids = await self.vector_store.add_documents(
                texts=texts,
                metadata_list=metadata,
                batch_size=self.batch_size
            )
            
            # Update stats
            self.stats.successful_files += 1
            self.stats.total_chunks += len(chunks)
            # Estimate tokens (rough approximation)
            self.stats.total_tokens += sum(len(text.split()) * 1.3 for text in texts)
            
            logger.info(f"Successfully processed {pdf_path} - {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_path}: {str(e)}")
            self.stats.failed_files += 1
            self.stats.errors[str(pdf_path)] = str(e)
            return False
            
    async def process_directory(self, 
                              dir_path: Path,
                              recursive: bool = True) -> ProcessingStats:
        """
        Process all PDFs in a directory.
        
        Args:
            dir_path: Directory containing PDFs
            recursive: Whether to process subdirectories
            
        Returns:
            ProcessingStats with processing results
        """
        start_time = time.time()
        
        # Reset stats
        self.stats = ProcessingStats(0, 0, 0, 0, 0, 0.0, {})
        
        # Find all PDFs
        pattern = "**/*.pdf" if recursive else "*.pdf"
        pdf_paths = list(dir_path.glob(pattern))
        self.stats.total_files = len(pdf_paths)
        
        # Process files
        for pdf_path in pdf_paths:
            await self.process_pdf(pdf_path)
            
        # Update final stats
        self.stats.processing_time = time.time() - start_time
        
        # Log summary
        logger.info(
            f"Processed {self.stats.successful_files}/{self.stats.total_files} files "
            f"({self.stats.total_chunks} chunks) in {self.stats.processing_time:.1f}s"
        )
        
        if self.stats.failed_files:
            logger.warning(f"Failed to process {self.stats.failed_files} files")
            
        return self.stats
        
    def get_stats(self) -> ProcessingStats:
        """Get current processing statistics."""
        return self.stats