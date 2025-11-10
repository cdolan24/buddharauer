# Document Processing Pipeline Documentation

## Overview

The document processing pipeline is responsible for:
1. Extracting text from PDFs
2. Creating semantic chunks
3. Generating embeddings
4. Storing vectors for retrieval

## Components

### 1. Semantic Chunker (`src/pipeline/chunker.py`)

#### Classes

**`TextChunk`**
```python
@dataclass
class TextChunk:
    text: str              # The chunk text
    page_number: int       # Source page number
    chunk_index: int       # Position in chunk sequence
    total_chunks: int      # Total chunks for document
    metadata: dict         # Associated metadata
```

**`SemanticChunker`**
- Primary class for text chunking
- Configurable chunk size and overlap
- Automatic size optimization
- Metadata preservation

**`ChunkPipeline`**
- Handles batch processing of documents
- Tracks processing statistics
- Provides progress information

### 2. Vector Store (`src/database/vector_store.py`)

#### Features
- Batched document processing
- Async operations
- Metadata filtering
- Persistence support
- ChromaDB-compatible interface

#### Key Methods
```python
async def add_documents(
    texts: List[str],
    metadata_list: List[Dict],
    batch_size: int = 32
) -> List[str]
```

### 3. Pipeline Orchestrator (`src/pipeline/orchestrator.py`)

#### Classes

**`ProcessingStats`**
```python
@dataclass
class ProcessingStats:
    total_files: int
    successful_files: int
    failed_files: int
    total_chunks: int
    total_tokens: int
    processing_time: float
    errors: Dict[str, str]
```

**`PipelineOrchestrator`**
- Coordinates pipeline components
- Handles error recovery
- Provides progress tracking
- Manages batch processing

## Usage Examples

### Basic Usage

```python
# Initialize components
chunker = SemanticChunker(chunk_size=500, chunk_overlap=50)
pipeline = ChunkPipeline(chunker, optimize_chunks=True)
vector_store = VectorStore(persist_directory="data/vector_db")

# Create orchestrator
orchestrator = PipelineOrchestrator(
    chunk_pipeline=pipeline,
    vector_store=vector_store,
    batch_size=32
)

# Process documents
stats = await orchestrator.process_directory(
    Path("data/documents"),
    recursive=True
)

# Get results
print(f"Processed {stats.successful_files}/{stats.total_files} files")
print(f"Created {stats.total_chunks} chunks")
print(f"Processing time: {stats.processing_time:.1f}s")
```

### Configuration

#### Chunk Size Optimization
```python
chunker = SemanticChunker()
optimal_size = get_optimal_chunk_size(
    text,
    target_chunks=10,
    min_size=100,
    max_size=2000
)
chunker.chunk_size = optimal_size
```

#### Batch Processing
```python
# Configure batch size for vector operations
orchestrator = PipelineOrchestrator(
    chunk_pipeline=pipeline,
    vector_store=vector_store,
    batch_size=32  # Adjust based on memory/performance
)
```

## Error Handling

The pipeline implements multiple levels of error handling:

1. **PDF Processing**
   - Handles corrupted files
   - Manages encryption errors
   - Recovers from timeout issues

2. **Chunking**
   - Validates chunk sizes
   - Handles empty documents
   - Preserves document structure

3. **Vector Store**
   - Manages embedding failures
   - Handles storage errors
   - Provides transaction rollback

## Testing

### Test Files
- `tests/unit/test_chunking_integration.py`
- `tests/unit/test_orchestrator.py`

### Running Tests
```bash
pytest tests/unit/
pytest tests/unit/ --cov=src/pipeline
```

## Performance Considerations

1. **Memory Management**
   - Batch processing for large documents
   - Streaming for vector operations
   - Configurable chunk sizes

2. **Optimization**
   - Parallel processing where possible
   - Caching for frequently accessed data
   - Efficient vector operations

3. **Scalability**
   - Designed for ChromaDB migration
   - Supports large document collections
   - Handles concurrent operations

## Future Improvements

1. **ChromaDB Integration**
   - Migrate from numpy implementation
   - Add advanced filtering
   - Improve search performance

2. **Progress Tracking**
   - Real-time progress updates
   - Detailed statistics
   - Performance monitoring

3. **Error Recovery**
   - Checkpoint system
   - Automatic retries
   - Partial success handling

## Maintenance

### Logging
The pipeline uses structured logging:
```python
logger = get_logger(__name__)
logger.info("Processing document: %s", pdf_path)
logger.error("Failed to process: %s", error)
```

### Monitoring
Track key metrics:
- Processing time
- Success/failure rates
- Chunk statistics
- Memory usage

### Backup
- Vector store data is persisted
- Regular backups recommended
- Transaction logging available

---

*Last updated: November 10, 2025*