# Architecture Plan - Buddharauer PDF Analysis System

## Overview
This is a Python-based AI agent application using FastAgent (fast-agent-mcp) to analyze PDF documents and provide intelligent question-answering and content summarization capabilities.

## Technology Stack

### Core Framework
- **FastAgent (fast-agent-mcp)**: MCP-native agent framework for building AI workflows
  - Version: 0.3.17+
  - Python requirement: >=3.13.5, <3.14
  - Installation: `uv pip install fast-agent-mcp`

### Package Management
- **uv**: Modern Python package and environment manager
  - Installation: Follow uv installation guide
  - Usage: `uv pip install`, `uv venv`, etc.

### Vector Database Options
Choose one based on requirements:
1. **ChromaDB** (Recommended for simplicity)
   - Lightweight, easy to set up
   - Good for prototyping and small-to-medium datasets
   - Python-native with minimal dependencies

2. **Qdrant**
   - High performance, production-ready
   - Excellent for scaling
   - Good REST API and Python client

3. **Weaviate**
   - Feature-rich with GraphQL support
   - Good for complex queries
   - Cloud-native architecture

### PDF Processing
- **PyMuPDF (fitz)** or **pdfplumber**: PDF text extraction
- **python-docx** or **mistune**: Markdown generation
- **LangChain** or native FastAgent capabilities: Text chunking and embeddings

### LLM Provider
- FastAgent supports: Anthropic (Claude), OpenAI (GPT), Google (Gemini)
- Also supports Azure, Ollama, Deepseek via TensorZero
- Recommendation: Start with Anthropic Claude for best reasoning

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Application                      │
│              (FastAgent Interactive Interface)              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                       │
│              (FastAgent Workflow Manager)                   │
├─────────────────────────────────────────────────────────────┤
│  • Question Answering Agent                                 │
│  • Summarization Agent                                      │
│  • Categorization Agent                                     │
│  • Entity Extraction Agent                                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   Vector DB  │ │ Document     │ │  Metadata    │
    │   (Embeddings│ │   Store      │ │   Store      │
    │    Search)   │ │ (Markdown)   │ │   (JSON)     │
    └──────────────┘ └──────────────┘ └──────────────┘
            ▲               ▲               ▲
            └───────────────┴───────────────┘
                            │
                ┌───────────┴────────────┐
                ▼                        ▼
        ┌──────────────┐         ┌──────────────┐
        │ PDF Ingestion│         │  Monitoring  │
        │   Pipeline   │         │  & Logging   │
        └──────────────┘         └──────────────┘
```

### Directory Structure

```
buddharauer/
├── data/                      # Raw PDF files
│   └── *.pdf
├── processed/                 # Processed output
│   ├── text/                 # Extracted text files
│   ├── markdown/             # Converted markdown files
│   └── metadata/             # Document metadata (JSON)
├── src/
│   ├── agents/               # FastAgent agent definitions
│   │   ├── qa_agent.py
│   │   ├── summarization_agent.py
│   │   ├── categorization_agent.py
│   │   └── extraction_agent.py
│   ├── pipeline/             # Data processing pipeline
│   │   ├── pdf_extractor.py
│   │   ├── text_processor.py
│   │   ├── markdown_converter.py
│   │   └── embeddings_generator.py
│   ├── database/             # Vector DB interface
│   │   ├── vector_store.py
│   │   └── query_manager.py
│   ├── models/               # Data models
│   │   ├── document.py
│   │   ├── entity.py
│   │   └── query.py
│   ├── client/               # User interface
│   │   └── cli.py
│   └── utils/                # Utilities
│       ├── config.py
│       └── logging.py
├── specs/                    # Documentation
├── tests/                    # Test suite
├── .env.example             # Environment template
├── pyproject.toml           # Python project config
├── uv.lock                  # Dependency lock file
├── CLAUDE.md               # AI assistant context
└── README.md               # Project overview
```

## Data Flow

### 1. Ingestion Pipeline
```
PDF Files → Text Extraction → Text Cleanup →
Markdown Conversion → Chunking → Embedding Generation →
Vector DB Storage + Metadata Storage
```

### 2. Query Processing
```
User Query → Agent Router → Context Retrieval (Vector DB) →
Agent Processing → Response Generation → User Interface
```

### 3. Entity Extraction
```
Processed Documents → NER/Entity Extraction →
Structured Storage (Characters, Locations, Items) →
Categorization & Tagging
```

## Agent Design

### Question Answering Agent
- **Purpose**: Answer specific questions about document content
- **Tools**: Vector search, document retrieval, citation generation
- **Prompt Strategy**: RAG-based with context window management

### Summarization Agent
- **Purpose**: Generate summaries of characters, locations, items, stories
- **Tools**: Document access, entity database, aggregation functions
- **Prompt Strategy**: Structured output with templates

### Categorization Agent
- **Purpose**: Filter and categorize entities by attributes
- **Tools**: Entity search, filtering logic, relationship mapping
- **Prompt Strategy**: Query understanding + structured filtering

### Entity Extraction Agent
- **Purpose**: Extract and classify entities from documents
- **Tools**: NER capabilities, schema validation, deduplication
- **Prompt Strategy**: Few-shot learning with entity schemas

## Scalability Considerations

### Phase 1: Prototype (Current)
- Local vector database
- Single-user CLI interface
- Synchronous processing
- Small dataset (<100 PDFs)

### Phase 2: Enhanced
- Persistent vector database with backups
- Web interface (FastAPI + React/Streamlit)
- Asynchronous processing for large documents
- Medium dataset (100-1000 PDFs)

### Phase 3: Production (Future)
- Cloud-hosted vector database
- Multi-user support with authentication
- Distributed processing
- Large dataset (1000+ PDFs)
- API for external integrations

## Security & Privacy

- Sensitive data in `.env` (API keys, database credentials)
- No credentials in code or version control
- Input validation for user queries
- Rate limiting on API calls
- Audit logging for document access

## Performance Targets

- PDF processing: <30 seconds per document
- Query response: <3 seconds for simple queries
- Entity extraction: <1 minute per document
- Batch processing: 10+ documents in parallel
