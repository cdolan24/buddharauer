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
- **PyMuPDF (fitz)** or **pdfplumber**: PDF text extraction and image extraction
- **python-docx** or **mistune**: Markdown generation
- **LangChain** or native FastAgent capabilities: Text chunking and embeddings
- **PIL/Pillow**: Image processing and manipulation
- **pytesseract** or cloud OCR: Text extraction from images (headings, captions)

### LLM Provider
- FastAgent supports: Anthropic (Claude), OpenAI (GPT), Google (Gemini)
- Also supports Azure, Ollama, Deepseek via TensorZero
- Recommendation: Start with Anthropic Claude for best reasoning
- **Vision Models**: Claude or GPT-4 Vision for image description and analysis

### Authentication & User Management
- **bcrypt** or **argon2**: Password hashing
- **SQLite**: User database and audit logs
- **JWT** or session files: Session management

### Analytics & Monitoring
- **SQLite**: Query logs, metrics storage, document registry
- **Pandas**: Data analysis for usage analytics
- **rich**: Terminal UI for status displays

## System Architecture

### High-Level Components

```
┌────────────────────────────────────────────────────────────────┐
│                    Client Application Layer                     │
│  ┌──────────────────┐  ┌────────────────────────────────────┐  │
│  │ CLI Interface    │  │  Authentication & Session Mgmt      │  │
│  │ (Faraday: User)  │  │  (Login, User Roles, Permissions)   │  │
│  │ (Albert: Admin)  │  │                                     │  │
│  └──────────────────┘  └────────────────────────────────────┘  │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                           │
│              (FastAgent Workflow Manager)                       │
├────────────────────────────────────────────────────────────────┤
│  • Question Answering Agent (with explanatory responses)        │
│  • Summarization Agent (creative context)                       │
│  • Categorization Agent (filtering & discovery)                 │
│  • Entity Extraction Agent (characters, locations, items)       │
│  • Image Description Agent (visual analysis)                    │
└────────────────────────────┬───────────────────────────────────┘
                             │
         ┌───────────────────┼────────────────────┐
         ▼                   ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   Vector DB      │ │ Document Store   │ │ Image Store      │
│   (Embeddings)   │ │ (Text/Markdown)  │ │ (PNG/JPEG)       │
│   + Search       │ │ + Metadata (JSON)│ │ + Manifests      │
└──────────────────┘ └──────────────────┘ └──────────────────┘
         ▲                   ▲                    ▲
         └───────────────────┼────────────────────┘
                             │
         ┌───────────────────┼────────────────────┐
         ▼                   ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ PDF Ingestion    │ │ Analytics &      │ │ User Management  │
│ Pipeline         │ │ Monitoring       │ │ & Audit Logs     │
│ (Text + Images)  │ │ (Metrics, Logs)  │ │ (SQLite)         │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Directory Structure

```
buddharauer/
├── data/                      # Raw PDF files (gitignored)
│   └── *.pdf
├── processed/                 # Processed outputs (gitignored)
│   ├── text/                 # Extracted text files
│   ├── markdown/             # Converted markdown files
│   ├── metadata/             # Document metadata (JSON)
│   └── images/               # Extracted images (NEW)
│       └── {document_name}/
│           ├── covers/       # Cover images
│           ├── chapters/     # Chapter heading images
│           ├── illustrations/# Illustrations and diagrams
│           └── manifest.json # Image metadata
├── src/
│   ├── agents/               # FastAgent agent definitions
│   │   ├── qa_agent.py                # Question answering (explanatory)
│   │   ├── summarization_agent.py     # Summarization (creative context)
│   │   ├── categorization_agent.py    # Entity filtering
│   │   ├── extraction_agent.py        # Entity extraction
│   │   └── image_agent.py             # Image description (NEW)
│   ├── pipeline/             # Data processing pipeline
│   │   ├── pdf_extractor.py           # Text + image extraction
│   │   ├── text_processor.py
│   │   ├── markdown_converter.py
│   │   ├── embeddings_generator.py
│   │   └── image_processor.py         # Image extraction & classification (NEW)
│   ├── database/             # Database interfaces
│   │   ├── vector_store.py            # Vector DB (ChromaDB/Qdrant)
│   │   ├── query_manager.py           # Query interface
│   │   ├── document_registry.py       # Document tracking (NEW)
│   │   └── user_database.py           # User management (NEW)
│   ├── models/               # Data models
│   │   ├── document.py
│   │   ├── entity.py
│   │   ├── query.py
│   │   ├── image.py                   # Image metadata (NEW)
│   │   └── user.py                    # User model (NEW)
│   ├── client/               # User interface
│   │   ├── cli.py                     # Main CLI
│   │   ├── auth.py                    # Authentication (NEW)
│   │   └── admin_commands.py          # Admin CLI commands (NEW)
│   ├── analytics/            # Analytics & monitoring (NEW)
│   │   ├── query_logger.py            # Query logging
│   │   ├── metrics.py                 # Metrics collection
│   │   └── reports.py                 # Report generation
│   └── utils/                # Utilities
│       ├── config.py
│       ├── logging.py
│       ├── auth_utils.py              # Password hashing, sessions (NEW)
│       └── image_utils.py             # Image processing helpers (NEW)
├── data_storage/             # System databases (gitignored, NEW)
│   ├── users.db             # User database (SQLite)
│   ├── query_log.db         # Query logs (SQLite)
│   ├── document_registry.db # Document tracking (SQLite)
│   └── audit_log.txt        # Audit trail
├── specs/                    # Documentation
│   ├── architecture.md
│   ├── data-processing-pipeline.md
│   ├── user-stories-detailed.md
│   ├── implementation-phases.md
│   ├── IMPLEMENTATION_NOTES.md
│   └── README.md
├── tests/                    # Test suite
│   ├── test_pipeline/
│   ├── test_agents/
│   ├── test_auth/            # Authentication tests (NEW)
│   └── test_images/          # Image processing tests (NEW)
├── .env.example             # Environment template
├── .gitignore              # Git ignore rules
├── pyproject.toml          # Python project config
├── uv.lock                 # Dependency lock file (auto-generated)
├── CLAUDE.md              # AI assistant context
└── README.md              # Project overview
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
