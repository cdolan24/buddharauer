# Development Notes

> **Note**: Main implementation tracking has moved to `IMPLEMENTATION_PROGRESS.md`.
> This file contains development patterns, guidelines, and technical decisions.

## Development Patterns

### 1. Code Structure

#### Module Organization
- Business logic in `src/pipeline/`
- Data access in `src/database/`
- Utilities in `src/utils/`
- Tests mirror source structure

#### Testing Strategy
- Unit tests for all components
- Integration tests for workflows
- Coverage target: >80%
- Test data in `tests/data/`

#### Error Handling Pattern
```python
try:
    result = operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise OperationError(f"Friendly message: {e}") from e
```

#### Embedding Generation
- Implemented in `src/pipeline/embeddings.py`
- Using Ollama's nomic-embed-text model
- Async implementation with httpx
- Cache implementation in `data/cache/embeddings`
- Batch size: 100 chunks per batch
- API endpoint: http://localhost:11434/api/embeddings
- Response format: `{"embedding": [float]}` (not "embeddings" plural)

### 2. Testing Infrastructure

#### Test Organization
- Unit tests in `tests/unit/`
- Test data in `tests/data/`
- Using pytest and pytest-asyncio
- All tests passing as of last commit

#### Test Files
- `test_pdf_extractor.py`
- `test_chunker.py`
- `test_embeddings.py`
- `test_paths.py`

#### Test Data
- Sample PDFs in `tests/data/`
- Embedding cache in `tests/data/test_cache/embeddings/`

### 3. Environment Setup

#### Python Environment
- Python 3.13.3
- Virtual environment in `.venv/`
- Key packages:
  - httpx for async HTTP
  - PyMuPDF for PDF processing
  - pytest and pytest-asyncio for testing

#### Ollama Setup
- Model: nomic-embed-text
- Status: Installed and working
- Size: 274 MB
- Command to verify: `ollama list`

### 4. Current Issues

#### Completed
- #1 PDF Text Extraction
- #2 Semantic Chunking
- #3 Initial Embedding Tasks
- #4 Embedding Generation Implementation

#### In Progress/Next
- #5 Vector Store Integration (Next Priority)
- #6 Embedding System Improvements

### 5. Known Quirks/Gotchas

1. Embedding API:
   - Use `/api/embeddings` (plural) for endpoint
   - But response has "embedding" (singular) key
   - Response format: `{"embedding": [float]}`

2. Path Handling:
   - Using `Path` from pathlib
   - Cache paths use SHA256 of content
   - All paths should be absolute

3. Async Testing:
   - Must use `@pytest.mark.asyncio`
   - Tests run in strict mode
   - Cache affects test isolation

### 6. Completed Since Last Update

#### Session 3 (Nov 10, 2025) - Test Fixes ✅

**Fixed 7 failing tests (84% → 96% passing)**:

1. **Embeddings Tests (2 fixed)**:
   - `test_embedding_caching`: Fixed cache collision issues with unique timestamped text
   - `test_progress_tracking`: Ensured cache misses to trigger API calls

2. **PDF Error Handling Tests (5 fixed)**:
   - `test_encrypted_pdf`: Updated for retry decorator behavior
   - `test_invalid_pdf`: Updated for retry decorator behavior
   - `test_extraction_timeout`: Fixed time.time() mocking (6 calls for retry loop)
   - `test_retry_logic`: Rewrote to test decorator directly
   - `test_directory_processing_with_errors`: Added all PDFMetadata fields

3. **Monitoring Test (1 fixed)**:
   - `test_progress_eta_calculation`: Fixed division-by-zero bug

4. **Vector Store Test (1 fixed)**:
   - `test_search_error_cases`: Fixed for ChromaDB API behavior

**Code Changes**:
- `src/pipeline/monitoring.py`: Added guard clause for elapsed=0 in ETA calculation

**Key Learnings**:
- Cache persistence between test runs can cause issues - use unique test data
- Retry decorators wrap exceptions - tests must expect wrapped exception types
- ChromaDB API returns `[[]]` for empty results, not `[]`
- Time mocking needs careful planning for retry loops

#### Session 2 (Nov 10, 2025) - API Enhancements

1. **PDF Extractor API Improvements** (✓):
   - Enhanced `extract_metadata()` to accept both Path and Document objects
   - Added `extract_pages()` convenience method
   - Improved error handling for corrupted and encrypted PDFs
   - Fixed compatibility with chunker integration
   - All chunking integration tests now passing (7/7)

2. **Embeddings Module Enhancements** (✓):
   - Added `cache_dir` property to EmbeddingGenerator
   - Fixed `httpx.TimeoutError` to `httpx.TimeoutException`
   - Improved batch processing return type documentation
   - Fixed all basic embedding tests (4/4 passing)
   - Enhanced test mocking for async operations (12/12 passing)

3. **Code Quality Improvements** (✓):
   - Added comprehensive docstrings to new methods
   - Improved type hints throughout modules
   - Better error messages and logging
   - Fixed test compatibility issues

4. Vector Store Improvements (✓ - Previous Session):
   - Fixed metadata filtering in search function
   - Added comprehensive test suite for filtering
   - Test cases passing with embedded document cache
   - Identified areas for coverage improvement
   - Current coverage: 24% (Target: 90%)

5. Previously Completed (✓):
   - Created `src/database/vector_store.py`
   - Implemented numpy-based temporary solution
   - Added document storage and search
   - ChromaDB-compatible API for future migration

### 7. Next Development Tasks (Updated Nov 10, 2025 - Session 4)

**Session 4 Completed Tasks** ✅:

1. ✅ **Fixed Last 3 Test Failures** (High Priority):
   - Fixed `test_orchestrator.py::test_process_pdf` - Used valid PDF fixtures
   - Fixed `test_orchestrator.py::test_batched_processing` - Used valid PDF fixtures
   - Fixed `test_recovery.py::test_orchestrator_recovery` - Corrected recovery state logic
   - **Current Status: 75/75 tests passing (100%)** ✅

2. ✅ **Improved Test Coverage** (High Priority):
   - **Achieved 92.13% overall coverage** (target: >90%) ✅
   - All modules above 75% coverage
   - Vector store: 89%, Chunker: 98%, Embeddings: 79%, PDF Extractor: 89%
   - Orchestrator: 94%, Recovery: 93%, Monitoring: 98%

3. ✅ **Code Cleanup** (Medium Priority):
   - Removed ~50 lines of duplicate code
   - Consolidated retry decorators (removed duplicate from pdf_extractor.py)
   - Extracted validation logic in VectorStore
   - Added comprehensive docstrings and comments to vector_store.py
   - Standardized error messages

4. ✅ **Documentation Updates** (Medium Priority):
   - Added docstrings to public API methods (cosine_similarity, delete_collection, get_collection_stats)
   - Added inline comments explaining complex algorithms (batch processing, numpy operations)
   - Enhanced process_batch() nested function documentation
   - Added warning documentation for destructive operations

**Immediate Priorities for Next Session**:

1. **API Documentation** (High Priority):
   - Create API reference documentation for vector_store module
   - Document embedding cache behavior and configuration
   - Add architecture diagrams for pipeline flow
   - Document recovery system usage patterns

2. **Performance Optimization** (Medium Priority):
   - Profile embeddings generation for large batches
   - Optimize vector similarity search for large collections
   - Add performance benchmarks for pipeline components
   - Consider implementing early stopping for searches

5. Vector Store Test Coverage (Previously Planned):
   Target: 90% coverage (currently 24%)
   - Document class implementation
   - Vector operations (cosine_similarity)
   - File operations (_load_documents)

6. Performance Optimization (Future):
   - Search algorithm efficiency
   - Memory usage optimization
   - Batch processing improvements

7. ChromaDB Migration Planning (Future - Q4):
   - Document current API surface
   - Test ChromaDB compatibility
   - Create migration scripts

### 7. Code Patterns

1. Async Pattern:
```python
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data)
```

2. Cache Pattern:
```python
cache_path = self._get_cache_path(text)
if cache_path.exists():
    return json.load(cache_path.open())["embedding"]
```

3. Batch Processing:
```python
for i in range(0, len(items), batch_size):
    batch = items[i:i + batch_size]
    results = await asyncio.gather(*[process(item) for item in batch])
```

### 8. Testing Patterns

1. Fixture Pattern:
```python
@pytest.fixture
def generator():
    return EmbeddingGenerator(cache_dir="tests/data/test_cache")
```

2. Async Test Pattern:
```python
@pytest.mark.asyncio
async def test_async_function(fixture):
    result = await fixture.async_method()
    assert result is not None
```

### 9. Directory Structure
```
src/
├── pipeline/
│   ├── __init__.py
│   ├── pdf_extractor.py
│   ├── chunker.py
│   └── embeddings.py
└── utils/
    ├── __init__.py
    └── paths.py

tests/
├── unit/
│   ├── test_pdf_extractor.py
│   ├── test_chunker.py
│   ├── test_embeddings.py
│   └── test_paths.py
├── conftest.py
└── data/
    ├── test.pdf
    └── test_cache/
        └── embeddings/
```