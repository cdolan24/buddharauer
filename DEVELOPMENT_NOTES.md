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

### 6. Completed Since Last Update (Nov 10, 2025)

1. Vector Store Improvements (✓):
   - Fixed metadata filtering in search function
   - Added comprehensive test suite for filtering
   - Test cases passing with embedded document cache
   - Identified areas for coverage improvement
   - Current coverage: 24% (Target: 90%)

2. Previously Completed (✓):
   - Created `src/database/vector_store.py`
   - Implemented numpy-based temporary solution
   - Added document storage and search
   - ChromaDB-compatible API for future migration

### 7. Next Development Tasks (Updated Nov 10, 2025)

1. Vector Store Test Coverage (High Priority):
   Target: 90% coverage (currently 24%)
   
   Key Areas:
   - Document class implementation
   - Vector operations (cosine_similarity)
   - File operations (_load_documents)
   - Error handling & edge cases
   - Metadata filtering system

2. Performance Optimization:
   Focus: Vector search and document processing
   
   Areas:
   - Search algorithm efficiency
   - Memory usage optimization
   - Batch processing improvements
   - Resource monitoring
   - Memory-mapped files

3. ChromaDB Migration Planning:
   Status: Planned for Q4
   
   Tasks:
   - Document current API surface
   - Test ChromaDB compatibility
   - Create migration scripts
   - Build wrapper class
   - Design rollback procedures

4. Documentation & Testing:
   Priority: High
   
   Updates:
   - API documentation
   - Migration guides
   - Performance benchmarks
   - Test patterns
   - Code examples

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