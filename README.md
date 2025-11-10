# Buddharauer - AI-Powered PDF Analysis System

An intelligent document analysis application built with FastAgent that enables semantic search, entity extraction, and interactive querying of PDF documents.

## Overview

Buddharauer processes PDF documents, extracts structured information (characters, locations, items), and provides an AI-powered interface for exploring and analyzing content without information overload.

## Technology Stack

- **Framework**: [FastAgent](https://fast-agent.ai/) (fast-agent-mcp) - MCP-native AI agent framework
- **Package Manager**: [uv](https://github.com/astral-sh/uv) - Modern Python package management
- **Python Version**: 3.13.5+
- **Vector Database**: ChromaDB (recommended) / Qdrant / Weaviate
- **LLM Provider**: Anthropic Claude (recommended) / OpenAI / Google

## Key Features

### Document Processing Pipeline
- Extract text from PDFs in the `data/` directory
- Convert to cleaned, structured markdown format
- Generate semantic embeddings for vector search
- Support for adding new documents retroactively

### AI-Powered Querying (User: Faraday)
- **Question Answering**: Ask natural language questions about document content with citations
- **Summarization**: Get concise summaries of characters, locations, items, and stories
- **Categorization**: Filter and categorize entities by attributes (e.g., "all male characters in Bree")
- **Entity Extraction**: Automatically identify and structure characters, locations, and items

### Administration
- Add/remove PDFs dynamically
- Monitor processing status
- Reprocess documents as needed
- View system health and performance metrics

## Project Structure

```
buddharauer/
├── data/                 # Raw PDF files (input)
├── processed/           # Processed outputs
│   ├── text/           # Extracted text
│   ├── markdown/       # Converted markdown
│   └── metadata/       # Document metadata
├── src/                # Source code
│   ├── agents/        # FastAgent agent definitions
│   ├── pipeline/      # Processing pipeline
│   ├── database/      # Vector database interface
│   ├── models/        # Data models
│   ├── client/        # CLI interface
│   └── utils/         # Utilities
├── specs/             # Detailed specifications
│   ├── architecture.md
│   ├── data-processing-pipeline.md
│   ├── user-stories-detailed.md
│   └── implementation-phases.md
├── tests/             # Test suite
└── CLAUDE.md          # AI assistant context
```

## Current Status

### Phase 0: Environment Setup ✅
- Development environment configured
- Project structure created
- Core dependencies installed
- Configuration system implemented
- Ollama integration verified

### Phase 1: Document Processing Pipeline 🚀
Currently implementing the document processing pipeline with three main components:

1. **PDF Text Extraction** ([Issue #1](https://github.com/cdolan24/buddharauer/issues/1))
   - Module: `src/pipeline/pdf_extractor.py`
   - Status: In Progress
   - Next: Implement PyMuPDF integration

2. **Semantic Chunking** ([Issue #2](https://github.com/cdolan24/buddharauer/issues/2))
   - Module: `src/pipeline/chunker.py`
   - Status: Planned
   - Next: Set up LangChain chunking

3. **Embedding Generation** ([Issue #3](https://github.com/cdolan24/buddharauer/issues/3))
   - Module: `src/pipeline/embeddings.py`
   - Status: Planned
   - Next: Integrate Ollama embeddings

### Next Steps
1. Complete PDF text extraction module
2. Implement semantic chunking with configurable parameters
3. Set up embedding generation with nomic-embed-text

## Documentation

Detailed specifications available in the `specs/` directory:
- [Architecture Plan](specs/architecture.md) - System design and components
- [Data Processing Pipeline](specs/data-processing-pipeline.md) - PDF to searchable content workflow
- [User Stories](specs/user-stories-detailed.md) - Detailed requirements and use cases
- [Implementation Phases](specs/implementation-phases.md) - Development roadmap

## Implementation Suggestions

### Recommended Vector Databases

1. **ChromaDB** (Recommended for MVP)
   - Lightweight and easy to set up
   - Great for prototyping and small-to-medium datasets
   - Python-native with minimal dependencies
   - Installation: `uv pip install chromadb`

2. **Qdrant** (Recommended for Production)
   - High performance, production-ready
   - Excellent scaling capabilities
   - Good REST API and Python client
   - Installation: `uv pip install qdrant-client`

3. **Weaviate** (Advanced Use Cases)
   - Feature-rich with GraphQL support
   - Good for complex queries and relationships
   - Cloud-native architecture

### Recommended PDF Processing Libraries

- **PyMuPDF (fitz)**: Fast and reliable text extraction
  - `uv pip install pymupdf`
- **pdfplumber**: Good for tables and structured data
  - `uv pip install pdfplumber`

### Recommended Embedding Models

- **OpenAI**: `text-embedding-3-small` (cost-effective) or `text-embedding-3-large` (higher quality)
- **Open Source**: `sentence-transformers` models (e.g., `all-MiniLM-L6-v2`)

### FastAgent Setup

```bash
# Install FastAgent
uv pip install fast-agent-mcp

# Initialize project with examples
fast-agent setup

# Run interactive session
fast-agent go
```

### Development Tools

- **Testing**: pytest, pytest-asyncio
- **Code Quality**: ruff (linter), black (formatter)
- **Type Checking**: mypy
- **Documentation**: mkdocs or sphinx

### Configuration Management

Create `.env` file for sensitive configuration:
```env
# LLM API Keys
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Vector Database
VECTOR_DB_TYPE=chromadb
VECTOR_DB_PATH=./vector_db

# Processing
CHUNK_SIZE=800
CHUNK_OVERLAP=150
EMBEDDING_MODEL=text-embedding-3-small
```

### Performance Optimizations

- **Batch Processing**: Process embeddings in batches of 100 chunks
- **Caching**: Cache embeddings to avoid regeneration
- **Parallel Processing**: Use async/await for concurrent operations
- **Chunking Strategy**: 500-1000 tokens per chunk with 100-200 token overlap

### Quality Assurance

- Target >80% test coverage for MVP
- Unit tests for each pipeline stage
- Integration tests for full workflows
- Performance benchmarks for query response time (<5 seconds target)

## Getting Started

1. **Install Python 3.13.5+** and **uv package manager**
2. **Clone repository** and navigate to project directory
3. **Install dependencies**: `uv pip install fast-agent-mcp chromadb pymupdf`
4. **Add PDFs** to the `data/` directory
5. **Configure environment**: Copy `.env.example` to `.env` and add API keys
6. **Run setup**: `fast-agent setup` (follow FastAgent initialization)
7. **Process documents**: Run processing pipeline (to be implemented)
8. **Start querying**: `fast-agent go` for interactive session

## Current Status

Project is in **planning phase**. Specifications complete, ready for Phase 0 (Project Setup) implementation.

See [Implementation Phases](specs/implementation-phases.md) for detailed development roadmap.

## User Stories

### Primary User: Faraday
Faraday wants to understand document contents without being overwhelmed by information.

**Core Capabilities:**
- Ask questions about PDF content with cited answers
- Get summaries of stories, characters, locations, and items
- Categorize elements by attributes (e.g., "all male characters in Bree")
- Explore relationships between entities

### Admin Stories
- Add new PDFs to the system retroactively
- Monitor processing status and system health
- Manage document lifecycle (add, remove, reprocess)

## License

[Add license information]

## Contributing

[Add contribution guidelines]

## Support

For issues and questions, please refer to the documentation in the `specs/` directory or contact the development team.