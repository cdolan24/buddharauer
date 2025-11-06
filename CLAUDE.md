# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Buddharauer** is an AI-powered PDF analysis system built with FastAgent (fast-agent-mcp) that enables semantic search, entity extraction, and intelligent querying of document collections. The system processes PDFs to extract structured information (characters, locations, items) and provides a conversational interface for exploration.

**Primary User**: Faraday - needs to understand document contents without information overload through Q&A, summarization, and categorization.

## Technology Stack

- **Language**: Python 3.13.5+
- **Framework**: FastAgent (fast-agent-mcp v0.3.17+) - MCP-native AI agent framework
- **Package Manager**: uv (modern Python package management)
- **Vector Database**: ChromaDB (MVP) → Qdrant (production)
- **LLM Provider**: Anthropic Claude (primary), with OpenAI/Google support
- **PDF Processing**: PyMuPDF (fitz) or pdfplumber
- **Testing**: pytest, pytest-asyncio

## Project Structure

```
buddharauer/
├── data/                    # Raw PDF files (gitignored)
├── processed/              # Processing outputs (gitignored)
│   ├── text/              # Extracted text files
│   ├── markdown/          # Converted markdown
│   └── metadata/          # Document metadata (JSON)
├── src/
│   ├── agents/            # FastAgent agent definitions
│   │   ├── qa_agent.py           # Question answering
│   │   ├── summarization_agent.py # Content summarization
│   │   ├── categorization_agent.py # Entity filtering
│   │   └── extraction_agent.py    # Entity extraction
│   ├── pipeline/          # Data processing pipeline
│   │   ├── pdf_extractor.py
│   │   ├── text_processor.py
│   │   ├── markdown_converter.py
│   │   └── embeddings_generator.py
│   ├── database/          # Vector DB interface
│   │   ├── vector_store.py
│   │   └── query_manager.py
│   ├── models/            # Data models
│   │   ├── document.py
│   │   ├── entity.py
│   │   └── query.py
│   ├── client/            # User interface
│   │   └── cli.py
│   └── utils/             # Utilities
│       ├── config.py
│       └── logging.py
├── specs/                 # Detailed specifications (READ THESE!)
├── tests/                 # Test suite
└── .env                   # Config (gitignored, use .env.example)
```

## Development Commands

### Environment Setup
```bash
# Install uv package manager first
# Then install dependencies
uv pip install fast-agent-mcp chromadb pymupdf pytest

# Setup FastAgent
fast-agent setup

# Create environment file
cp .env.example .env
# Edit .env with API keys
```

### Running the Application
```bash
# Interactive FastAgent session
fast-agent go

# Process new PDFs (to be implemented)
python -m src.pipeline.process_documents

# Run with watch mode for auto-processing
python -m src.pipeline.process_documents --watch
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_pdf_extractor.py

# Run tests matching pattern
pytest -k "test_entity"
```

### Code Quality
```bash
# Lint with ruff
ruff check src/

# Format with black
black src/

# Type checking
mypy src/
```

## Architecture Highlights

### Data Flow
1. **Ingestion**: PDF → Text Extraction → Text Cleanup → Markdown Conversion
2. **Embedding**: Chunking (500-1000 tokens, 100-200 overlap) → Embeddings → Vector DB
3. **Querying**: User Query → Vector Search → Context Retrieval → Agent Processing → Response

### Agent Design Pattern
- **QA Agent**: RAG-based question answering with citations
- **Summarization Agent**: Template-based entity summaries
- **Categorization Agent**: Natural language query parsing + filtering
- **Extraction Agent**: NER + schema validation for entities

### Entity Schema
```python
# Character
{"id": "char_001", "name": str, "type": "character",
 "attributes": {"gender": str, "role": str, "species": str},
 "locations": [str], "mentions": int}

# Location
{"id": "loc_001", "name": str, "type": "location",
 "attributes": {"region": str, "type": str},
 "characters": [str], "mentions": int}
```

## Configuration

Key parameters in `src/utils/config.py`:
- `CHUNK_SIZE`: 800 tokens (adjustable 500-1000)
- `CHUNK_OVERLAP`: 150 tokens (adjustable 100-200)
- `EMBEDDING_MODEL`: "text-embedding-3-small" (OpenAI)
- `VECTOR_DB`: "chromadb" (or "qdrant")
- `LLM_PROVIDER`: "anthropic" (Claude)

Environment variables (`.env`):
- `ANTHROPIC_API_KEY`: Required for Claude
- `OPENAI_API_KEY`: Required for embeddings
- `VECTOR_DB_PATH`: "./vector_db"

## Important Implementation Notes

### FastAgent Usage
- Use declarative syntax for agent definitions
- Leverage MCP features (Sampling, Elicitations)
- Follow "Building Effective Agents" patterns from Anthropic
- Support for structured outputs, PDF, and vision built-in

### PDF Processing
- Handle corrupted PDFs gracefully (log, skip, notify)
- Preserve page references for citations
- Support incremental processing (watch mode)
- Implement retry logic for API failures

### Vector Database
- Use cosine similarity for search
- Batch upserts (100 chunks at a time)
- Cache embeddings to avoid regeneration
- Maintain document registry for tracking

### Entity Extraction
- Implement deduplication logic
- Validate against schemas
- Build relationship graph
- Store in JSON or SQLite

### Performance Targets
- PDF processing: <30 seconds per document
- Query response: <3 seconds
- Entity extraction: <1 minute per document
- Test coverage: >80% (MVP), >90% (production)

## Development Phases

**Current Status**: Planning phase complete, ready for Phase 0 (Project Setup)

See [specs/implementation-phases.md](specs/implementation-phases.md) for full roadmap:
- Phase 0: Project setup (Week 1)
- Phase 1: PDF processing pipeline (Week 2-3)
- Phase 2: Vector DB integration (Week 3-4)
- Phase 3: FastAgent basic QA (Week 4-5)
- Phase 4: Entity extraction (Week 5-6)
- Phase 5: Summarization (Week 6-7)
- Phase 6: Categorization (Week 7-8)
- Phase 7-10: CLI, management, testing, documentation

## Key User Stories

1. **Question Answering**: "Who is Aragorn?" → Answer with citations (page numbers)
2. **Summarization**: "Summarize all characters" → Grouped list with details
3. **Categorization**: "Show all male characters in Bree" → Filtered results
4. **Entity Detail**: "Detail Aragorn" → Full profile with relationships
5. **Document Management**: Add/remove PDFs dynamically with auto-processing

## Testing Strategy

- **Unit Tests**: Each pipeline stage, agent, database operation
- **Integration Tests**: Full workflows (PDF → Query → Response)
- **Performance Tests**: Large document sets, concurrent queries
- **Quality Tests**: Embedding quality, entity extraction accuracy
- Target: >80% coverage for MVP, >90% for production

## Security & Best Practices

- Never commit API keys (use .env)
- Validate user inputs in query processing
- Implement rate limiting for API calls
- Audit log for document access
- Input sanitization for file operations

## Common Gotchas

1. **FastAgent requires Python 3.13.5+**: Ensure correct version
2. **API costs**: Embedding generation costs add up, implement caching
3. **Chunking strategy**: Too small = loss of context, too large = poor retrieval
4. **Entity deduplication**: Same entities with different spellings need normalization
5. **PDF quality**: Image-only PDFs need OCR (future enhancement)

## Resources

- **FastAgent Docs**: https://fast-agent.ai/
- **FastAgent GitHub**: https://github.com/evalstate/fast-agent
- **Detailed Specs**: See [specs/](specs/) directory
- **Architecture**: [specs/architecture.md](specs/architecture.md)
- **Pipeline**: [specs/data-processing-pipeline.md](specs/data-processing-pipeline.md)
- **User Stories**: [specs/user-stories-detailed.md](specs/user-stories-detailed.md)

## Git Workflow

- Main branch: `main`
- Commit message format: Conventional Commits preferred
- Branch naming: `feature/`, `fix/`, `docs/`
- Always run tests before committing

## Notes for Future Sessions

When implementing, prioritize in this order:
1. Setup development environment (Phase 0)
2. Get basic PDF → Text → Markdown working (Phase 1)
3. Get one PDF searchable in vector DB (Phase 2)
4. Get basic Q&A working with one document (Phase 3)
5. Expand to entity extraction and other features

Focus on getting end-to-end pipeline working with ONE PDF before scaling to multiple documents.
