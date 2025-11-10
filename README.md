# Buddharauer - AI-Powered PDF Analysis System

An intelligent document analysis application with a chat-based interface that enables semantic search, entity extraction, and interactive querying of PDF documents using **local AI models**.

## Overview

Buddharauer processes large PDF documents, extracts structured information (characters, locations, items), and provides an AI-powered chat interface with side-by-side source document viewing. Built with local LLMs (via Ollama), it runs entirely on your infrastructure with no cloud dependencies.

## ✨ Key Features

### 🤖 Chat-Based Interface with Split Screen
- **Chat Window**: Natural conversation with AI agents
- **Document Viewer**: Side-by-side source document display
- **Live Citations**: Highlighted passages with page numbers
- **Context Preservation**: Multi-turn conversations with memory

### 📚 Document Processing Pipeline
- Extract text and images from large PDFs (1000+ pages supported)
- Intelligent chunking with semantic awareness
- Generate vector embeddings for semantic search
- Support for adding new documents retroactively

### 🎯 Multi-Agent System
- **Orchestrator Agent**: Routes user questions to specialized agents
- **Analyst Agent**: Summarizes data and provides creative insights
- **Web Search Agent**: Searches external sources when needed
- **Retrieval Agent**: Finds relevant chunks from vector database (RAG)

### 🏠 Local-First Architecture
- **No Cloud Dependencies**: All models run locally via Ollama
- **Configurable Models**: Choose models per agent based on your hardware
- **Privacy**: Your documents never leave your machine
- **Cost-Effective**: No API fees

## Technology Stack

### Core Infrastructure
- **Agent Framework**: [FastAgent](https://fast-agent.ai/) (fast-agent-mcp v0.3.17+)
  - MCP-native agent orchestration
  - Tool calling and structured generation
- **Backend**: FastAPI (Python REST API wrapping FastAgent agents)
- **Frontend**: Gradio (interactive web UI)
- **Package Manager**: uv (preferred) or pip + venv
- **Python**: 3.13.5+ (required for FastAgent)

### Local AI/ML
- **LLM Server**: [Ollama](https://ollama.ai/) - Local model server
  - Recommended models: llama3.2, qwen2.5, mistral, phi
  - OpenAI-compatible API (localhost:11434/v1)
  - Configurable model locations
- **FastAgent Integration**: Uses generic provider to connect to Ollama
  - Configuration via fastagent.config.yaml
  - Model specification: `generic.model_name:tag`

### Vector Database
- **ChromaDB** (recommended for MVP): Local, Python-native
- **Qdrant** (production): Higher performance, Docker deployment

### PDF Processing
- **PyMuPDF (fitz)**: Text + image extraction
- **Pillow**: Image processing
- **pytesseract** (optional): OCR for image-based text

### Additional Components
- **SQLite**: Metadata, user management, query logs
- **pytest**: Testing framework
- **bcrypt** (optional): Password hashing for authentication

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  Gradio Web Interface                      │
│   ┌─────────────────┐      ┌────────────────────────┐     │
│   │  Chat Window    │      │  Document Viewer       │     │
│   │  (User Q&A)     │      │  (Source PDFs/Markdown)│     │
│   └─────────────────┘      └────────────────────────┘     │
└──────────────────────┬─────────────────────────────────────┘
                       │ HTTP/REST API
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                            │
│   /api/chat, /api/documents, /api/search, /api/health      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│             FastAgent Orchestration Layer                   │
│  ┌──────────────┐ ┌──────────┐ ┌────────────┐ ┌────────┐  │
│  │Orchestrator  │ │ Analyst  │ │Web Search  │ │Retrieval│ │
│  │ (FastAgent)  │ │(FastAgent│ │ (FastAgent)│ │(FastAgent│ │
│  │generic.llama │ │ sub-agent│ │ +MCP tools)│ │ +RAG)   │ │
│  │3.2:latest    │ │)         │ │            │ │         │ │
│  └──────────────┘ └──────────┘ └────────────┘ └────────┘  │
│           FastAgent generic provider ↓                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│     Ollama Server (localhost:11434) - OpenAI Compatible     │
│     Models: llama3.2, qwen2.5, mistral, phi, etc.           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Storage                             │
│  [Vector DB]  [Documents]  [Images]  [SQLite Metadata]      │
└─────────────────────────────────────────────────────────────┘
```

## Recommended Models by Agent (FastAgent + Ollama)

| Agent | FastAgent Model Spec | Ollama Model | Speed | Quality | RAM | FastAgent Tested |
|-------|---------------------|--------------|-------|---------|-----|------------------|
| **Orchestrator** | `generic.llama3.2:latest` | llama3.2 | Medium | High | 8GB | ✅ Yes |
| **Orchestrator** (alt) | `generic.qwen2.5:latest` | qwen2.5 | Medium | High | 7GB | ✅ Yes |
| **Analyst** | `generic.llama3.2:latest` | llama3.2 | Medium | High | 8GB | ✅ Yes |
| **Web Search** | `generic.mistral:7b` | mistral:7b | Fast | Medium | 6GB | ⚠️ Limited |
| **Retrieval** | `generic.qwen2.5:latest` | qwen2.5 | Medium | High | 7GB | ✅ Yes |
| **Embeddings** | N/A (Ollama API) | nomic-embed-text | Fast | High | 2GB | N/A |

**Note**: FastAgent officially tests tool calling with `llama3.2:latest` and `qwen2.5:latest`. Other models may work but are not guaranteed.

**Alternative Models**:
- Low memory: `phi3:mini` (4GB), `mistral:7b` (6GB)
- High quality: `llama3:70b` (40GB), `qwen2:72b` (40GB)
- All models configurable in `fastagent.config.yaml` and `config.yaml`

## Hardware Requirements

### Minimum (Testing)
- **RAM**: 16GB
- **GPU**: Optional (CPU mode works)
- **Disk**: 20GB for models
- **Performance**: ~5-10s response time

### Recommended
- **RAM**: 32GB
- **GPU**: NVIDIA with 8GB+ VRAM (RTX 3070 or better)
- **Disk**: 50GB SSD
- **Performance**: ~2-3s response time

### Optimal
- **RAM**: 64GB
- **GPU**: NVIDIA with 16GB+ VRAM (RTX 4080/4090)
- **Disk**: 100GB+ NVMe SSD
- **Performance**: <1s response time

## 🚀 Quick Start

### 1. Install Prerequisites

```bash
# Install Python 3.13.5+ (required for FastAgent)
python --version

# Install uv (recommended) or use pip
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Ollama
# Visit: https://ollama.ai/download
# Or: curl -fsSL https://ollama.ai/install.sh | sh

# Pull recommended models for FastAgent
ollama pull llama3.2:latest
ollama pull qwen2.5:latest
ollama pull mistral:7b
ollama pull nomic-embed-text
```

### 2. Clone & Setup

```bash
# Clone repository
git clone https://github.com/yourusername/buddharauer.git
cd buddharauer

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Or with pip
pip install -r requirements.txt
```

### 3. Configure

```bash
# Setup FastAgent
fast-agent setup  # Creates fastagent.config.yaml

# Configure Ollama in fastagent.config.yaml:
# generic:
#   api_key: "ollama"
#   base_url: "http://localhost:11434/v1"

# Copy application config
cp config.example.yaml config.yaml

# Edit config.yaml to set:
# - FastAgent + Ollama integration
# - Model selections per agent (generic.model_name:tag)
# - Vector database settings
# - Chunking parameters
```

### 4. Add Documents

```bash
# Add PDFs to data/ directory
cp /path/to/your/documents/*.pdf data/

# Process documents
python scripts/process_documents.py
```

### 5. Start Application

```bash
# Start FastAPI backend (Terminal 1)
uvicorn src.api.main:app --reload --port 8000

# Start Gradio frontend (Terminal 2)
python src/frontend/app.py

# Or use the launcher script
python run.py
```

### 6. Access UI

Open browser to: **http://localhost:7860**

## 📁 Project Structure

```
buddharauer/
├── config.yaml              # Main configuration
├── config.example.yaml      # Configuration template
├── requirements.txt         # Python dependencies
├── run.py                   # Application launcher
│
├── data/                    # Raw PDF files (gitignored)
│   └── *.pdf
│
├── processed/               # Processed outputs (gitignored)
│   ├── text/               # Extracted text
│   ├── markdown/           # Converted markdown
│   ├── metadata/           # Document metadata (JSON)
│   └── images/             # Extracted images
│
├── vector_db/              # ChromaDB/Qdrant data (gitignored)
│
├── data_storage/           # SQLite databases (gitignored)
│   ├── documents.db       # Document registry
│   ├── query_log.db       # Query history
│   └── users.db           # User accounts (optional)
│
├── src/
│   ├── api/               # FastAPI backend
│   │   ├── main.py       # API entry point
│   │   ├── routes/       # API endpoints
│   │   │   ├── chat.py
│   │   │   ├── documents.py
│   │   │   └── search.py
│   │   └── models/       # Pydantic models
│   │
│   ├── agents/           # LangChain agents
│   │   ├── orchestrator.py
│   │   ├── analyst.py
│   │   ├── web_search.py
│   │   └── retrieval.py
│   │
│   ├── pipeline/         # Document processing
│   │   ├── pdf_extractor.py
│   │   ├── chunker.py
│   │   ├── embeddings.py
│   │   └── image_processor.py
│   │
│   ├── database/         # Database interfaces
│   │   ├── vector_store.py
│   │   ├── document_registry.py
│   │   └── query_logger.py
│   │
│   ├── frontend/         # Gradio UI
│   │   ├── app.py       # Main Gradio app
│   │   └── components/  # UI components
│   │
│   └── utils/           # Utilities
│       ├── config.py    # Config loader
│       ├── ollama_client.py
│       └── chunking.py  # Chunking strategies
│
├── tests/               # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/             # Utility scripts
│   ├── process_documents.py
│   ├── setup_models.py
│   └── benchmark.py
│
└── specs/               # Detailed specifications
    ├── ARCHITECTURE_V2.md
    ├── API.md
    ├── IMPLEMENTATION_PLAN.md
    └── README.md
```

## 🔧 Configuration

### fastagent.config.yaml (FastAgent LLM Provider)

```yaml
# FastAgent generic provider configuration for Ollama
generic:
  api_key: "ollama"  # Default for Ollama
  base_url: "http://localhost:11434/v1"  # Ollama OpenAI-compatible endpoint

# Optional: Override with environment variables
# GENERIC_API_KEY=ollama
# GENERIC_BASE_URL=http://localhost:11434/v1
```

### config.yaml (Application Configuration)

```yaml
# FastAgent + Ollama configuration
fastagent:
  provider: "generic"  # Use generic provider for Ollama
  ollama_base_url: "http://localhost:11434"
  models_path: "/path/to/ollama/models"  # Optional custom path

# Agent model selections (FastAgent model specs)
agents:
  orchestrator:
    model: "generic.llama3.2:latest"  # FastAgent model spec
    temperature: 0.7
    max_tokens: 2048

  analyst:
    model: "generic.llama3.2:latest"
    temperature: 0.5
    max_tokens: 4096

  web_search:
    model: "generic.mistral:7b"
    temperature: 0.3
    max_tokens: 1024

  retrieval:
    llm_model: "generic.qwen2.5:latest"  # For query reformulation
    embedding_model: "nomic-embed-text"  # Via Ollama embeddings API
    dimensions: 768

# Vector database
vector_db:
  type: "chromadb"  # or "qdrant"
  path: "./vector_db"

# Chunking for large PDFs
chunking:
  strategy: "semantic"  # semantic, fixed, recursive
  chunk_size: 800
  chunk_overlap: 150
  max_chunk_size: 1500
  min_chunk_size: 100

# API settings
api:
  host: "0.0.0.0"
  port: 8000

# Frontend settings
frontend:
  platform: "gradio"
  port: 7860
  theme: "soft"
  chat_history_length: 50
```

## 📖 Usage Examples

### Chat Interface

```
User: "Who is Aragorn?"

[Orchestrator Agent]: *Searches vector database*
[Retrieval Agent]: *Finds relevant chunks from fellowship.pdf*

System: "Aragorn is a central character who appears throughout the documents.

IDENTITY & ROLE:
Aragorn is a ranger - a wandering warrior and protector. He is human
and male, with a hidden noble heritage that becomes important to the story.

KEY LOCATIONS:
- Bree: Where he first appears (pages 3, 15)
- Rivendell: An elven refuge (page 87)

[Source: fellowship.pdf, pages 3, 15, 42, 87]"
```

### Document Viewer

The right panel shows the source document with highlighted citations, allowing you to verify the AI's responses.

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Test specific service
pytest tests/integration/test_api.py
pytest tests/unit/test_chunking.py
```

## 🛠️ Development

### Adding New Models

```bash
# Pull new model
ollama pull qwen2:7b

# Update config.yaml
# Test with specific agent
python scripts/test_agent.py --agent analyst --model qwen2:7b
```

### Processing New Documents

```bash
# Add PDFs to data/
# Run processing script
python scripts/process_documents.py --watch

# Or process specific file
python scripts/process_documents.py --file data/newdoc.pdf
```

### API Development

```bash
# Start with auto-reload
uvicorn src.api.main:app --reload

# View API docs
open http://localhost:8000/docs
```

## 📊 Monitoring

### System Health

```bash
# Check API health
curl http://localhost:8000/api/health

# View metrics
curl http://localhost:8000/api/analytics/metrics
```

### Query Analytics

```bash
# Popular queries
curl http://localhost:8000/api/analytics/popular-queries

# System stats
curl http://localhost:8000/api/analytics/stats
```

## 🗺️ Roadmap

### Current Status: Planning Phase

See [Implementation Plan](specs/IMPLEMENTATION_PLAN.md) for detailed roadmap.

### Phase 0: Project Setup (Week 1)
- [x] Architecture design
- [ ] Development environment setup
- [ ] Ollama installation and model downloads
- [ ] Basic project structure

### Phase 1: Backend Core (Week 2-3)
- [ ] FastAPI setup with core endpoints
- [ ] Document processing pipeline
- [ ] Vector database integration
- [ ] LangChain agent framework

### Phase 2: Agents (Week 3-4)
- [ ] Orchestrator agent implementation
- [ ] Analyst agent implementation
- [ ] Web search agent
- [ ] RAG retrieval system

### Phase 3: Frontend (Week 4-5)
- [ ] Gradio chat interface
- [ ] Document viewer component
- [ ] Source citation display
- [ ] Chat history management

### Phase 4: Testing & Polish (Week 5-6)
- [ ] Comprehensive test suite
- [ ] Performance optimization
- [ ] Documentation completion
- [ ] Deployment guide

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

[Add license information]

## 🙏 Acknowledgments

- **Ollama** - Local LLM server
- **LangChain** - Agent orchestration framework
- **Gradio** - Web UI framework
- **ChromaDB** - Vector database

## 📚 Documentation

Detailed specifications in `specs/` directory:
- [Architecture V2](specs/ARCHITECTURE_V2.md) - Complete system design
- [API Documentation](specs/API.md) - REST API reference
- [Implementation Plan](specs/IMPLEMENTATION_PLAN.md) - Development roadmap
- [User Stories](specs/user-stories-detailed.md) - Requirements

## Support

For issues and questions:
- **GitHub Issues**: [Report bugs or request features](https://github.com/yourusername/buddharauer/issues)
- **Documentation**: See `specs/` directory
- **Discussions**: [Community forum](https://github.com/yourusername/buddharauer/discussions)

---

**Note**: This is a local-first application. All processing happens on your machine. No cloud services or API keys required (except optional web search).
