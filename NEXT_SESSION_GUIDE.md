# Next Session Quick Start Guide

**Current Status**: Phase 2 Complete ✅ → Phase 3 Started (5%)
**Date**: 2025-11-11 (Updated)
**Next Phase**: Phase 3 - FastAgent Integration (IN PROGRESS)

---

## ⚡ Latest Session Progress (Session 7-8)

### Completed This Session
1. **Phase 2 Completion**
   - ✅ Chat endpoint with RAG (`POST /api/chat`, `GET /conversations`, `DELETE /conversations`)
   - ✅ 18 new integration tests (all passing)
   - ✅ ChatRequest/ChatResponse models with source citations
   - ✅ Full QueryLogger integration
   - ✅ Comprehensive documentation (SESSION_7_SUMMARY.md)
   - ✅ GitHub issue #22 closed

2. **Phase 3 Setup Started**
   - ✅ Verified FastAgent v0.3.23 installation
   - ✅ Updated `fastagent.config.yaml` with correct model names
   - ✅ Confirmed Ollama connectivity
   - ⏳ Started llama3.2:latest model download (2GB, ~2 min)

### Files Created/Modified This Session
- `src/api/routes/chat.py` (372 lines) - NEW
- `tests/integration/test_chat_endpoint.py` (385 lines) - NEW
- `SESSION_7_SUMMARY.md` - NEW
- `NEXT_SESSION_GUIDE.md` - UPDATED (this file)
- `fastagent.config.yaml` - UPDATED (llama2→llama3.2, qwen→qwen2.5)
- `src/api/models/requests.py` - UPDATED (added ChatRequest)
- `src/api/models/responses.py` - UPDATED (added ChatResponse, SourceReference)
- `src/api/routes/__init__.py` - UPDATED (added chat_router)
- `src/api/main.py` - UPDATED (registered chat_router)

### Test Results
```bash
✅ tests/integration/test_chat_endpoint.py - 18/18 PASSED
✅ tests/integration/test_api_basic.py - 21/21 PASSED
✅ Total: 39/39 integration tests passing (100%)
```

---

## Quick Status Check

### What's Complete
- ✅ Phase 0: Environment Setup
- ✅ Phase 1: Document Processing Pipeline
- ✅ Phase 2: FastAPI Backend (ALL ENDPOINTS)
  - Health, Documents, Search, **Chat** (NEW!)
  - 39 integration tests passing
  - QueryLogger fully integrated

### Phase 3 Progress (5% Complete)
- ✅ FastAgent v0.3.23 installed and verified
- ✅ Python 3.13.9 verified
- ✅ Ollama running and accessible
- ✅ `fastagent.config.yaml` updated with correct models
- ✅ nomic-embed-text model available
- ⏳ llama3.2:latest model downloading (required)
- 🔴 qwen2.5:latest model needed (not yet pulled)
- 🔴 mistral:7b model needed (not yet pulled)

### What's Next (Immediate)
- 📥 Complete model downloads (llama3.2, qwen2.5, mistral:7b)
- 🔧 Create FastAgent utility wrapper
- 🤖 Implement Retrieval Agent
- 🧪 Create agent unit tests

---

## Critical Files to Review

### Before Starting Phase 3, Read These:

1. **SESSION_7_SUMMARY.md** - Complete Phase 2 summary
2. **CLAUDE.md** - Project instructions and architecture
3. **specs/IMPLEMENTATION_PLAN.md** - Overall roadmap
4. **specs/ARCHITECTURE_V2.md** - Technical architecture

### Key Implementation Files:

1. **Chat Endpoint** (Ready for FastAgent)
   - `src/api/routes/chat.py` - Current basic RAG, needs FastAgent integration
   - `tests/integration/test_chat_endpoint.py` - 18 tests to update

2. **Dependencies System**
   - `src/api/dependencies.py` - Dependency injection
   - `src/api/main.py` - App initialization

3. **Models**
   - `src/api/models/requests.py` - ChatRequest model
   - `src/api/models/responses.py` - ChatResponse, SourceReference models

---

## Phase 3 Priorities (Week 3-4)

### Priority 1: FastAgent Setup (CRITICAL)

**Goal**: Get FastAgent working with Ollama

**Tasks**:
1. Verify FastAgent installation (v0.3.17+)
   ```bash
   pip list | grep fast-agent-mcp
   ```

2. Create `fastagent.config.yaml`:
   ```yaml
   generic:
     api_key: "ollama"
     base_url: "http://localhost:11434/v1"
   ```

3. Test Ollama connection:
   ```bash
   # Check Ollama is running
   curl http://localhost:11434/api/tags

   # Test FastAgent
   fast-agent --model generic.llama3.2:latest
   ```

4. Verify models are pulled:
   ```bash
   ollama list
   # Should see: llama3.2, qwen2.5, mistral:7b, nomic-embed-text
   ```

**Deliverable**: FastAgent successfully communicates with Ollama

**Related Issue**: #23 (Phase 3: Implement FastAgent Agents)

---

### Priority 2: Retrieval Agent (RAG)

**Goal**: Create FastAgent agent for vector database search

**Tasks**:
1. Create `src/agents/retrieval.py`:
   - Define FastAgent agent with qwen2.5 model
   - Create MCP tool for VectorStore access
   - Implement query reformulation
   - Add re-ranking logic

2. Create `src/utils/fastagent_client.py`:
   - Wrapper for FastAgent initialization
   - Configuration loading
   - Error handling

3. Test retrieval agent:
   - Unit tests for agent initialization
   - Integration tests with VectorStore
   - Test with real processed documents

**Deliverable**: Retrieval agent can search vector DB and return relevant chunks

**Files to Create**:
- `src/agents/retrieval.py`
- `src/agents/__init__.py`
- `src/utils/fastagent_client.py`
- `tests/unit/test_retrieval_agent.py`
- `tests/integration/test_fastagent_integration.py`

---

### Priority 3: Orchestrator Agent

**Goal**: Main agent that routes to sub-agents

**Tasks**:
1. Create `src/agents/orchestrator.py`:
   - Define main FastAgent agent (llama3.2)
   - Register retrieval agent as tool
   - Implement routing logic
   - Add conversation memory

2. Update chat endpoint:
   - Replace basic RAG with orchestrator call
   - Handle agent responses
   - Extract sources from agent output
   - Update error handling

3. Update tests:
   - Modify chat endpoint tests for FastAgent
   - Add orchestrator-specific tests
   - Test routing logic

**Deliverable**: Chat endpoint uses FastAgent orchestrator

**Files to Modify**:
- `src/api/routes/chat.py` (replace basic RAG)
- `tests/integration/test_chat_endpoint.py` (update for FastAgent)

---

## Quick Command Reference

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/integration/test_chat_endpoint.py -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run without coverage
pytest --no-cov
```

### Development Server
```bash
# Start FastAPI
uvicorn src.api.main:app --reload --port 8000

# Check API docs
# http://localhost:8000/docs

# Test health endpoint
curl http://localhost:8000/api/health
```

### Ollama
```bash
# Check status
ollama list

# Test model
ollama run llama3.2:latest

# Test embeddings
curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "test"
}'
```

### FastAgent
```bash
# Setup
fast-agent setup

# Test with Ollama
fast-agent --model generic.llama3.2:latest

# Interactive mode
fast-agent --model generic.llama3.2:latest --interactive
```

---

## Current Architecture

### Phase 2 (Current)
```
User → FastAPI → Chat Endpoint
              ↓
        QueryLogger (log)
              ↓
        VectorStore (search)
              ↓
        Basic Response (RAG)
              ↓
        QueryLogger (log)
              ↓
        Return Response
```

### Phase 3 (Goal)
```
User → FastAPI → Chat Endpoint
              ↓
        QueryLogger (log)
              ↓
        FastAgent Orchestrator
              ↓
    ┌─────────┬─────────┐
    ↓         ↓         ↓
Retrieval  Analyst  WebSearch
    ↓         ↓         ↓
    └─────────┴─────────┘
              ↓
        Synthesized Response
              ↓
        QueryLogger (log)
              ↓
        Return Response
```

---

## Code Style Requirements

**IMPORTANT**: All new code must follow these standards:

### Documentation
- **Docstrings**: All functions and classes (Google-style)
- **Type Hints**: All parameters and return types
- **Comments**: Explain WHY, not WHAT
- **Examples**: Include usage examples in docstrings

### Structure
- **Function Size**: < 50 lines ideally
- **Single Responsibility**: One function, one purpose
- **DRY**: Don't Repeat Yourself
- **Naming**: Clear, descriptive names

### Example
```python
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class AgentResponse:
    """Response from a FastAgent agent.

    Attributes:
        content: The generated text response
        sources: List of source chunks used
        metadata: Additional response metadata

    Example:
        >>> response = AgentResponse(
        ...     content="Aragorn is a ranger...",
        ...     sources=[{"chunk_id": "doc_001_chunk_042"}],
        ...     metadata={"model": "llama3.2"}
        ... )
    """
    content: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]


async def call_retrieval_agent(
    query: str,
    limit: int = 5
) -> AgentResponse:
    """Call the retrieval agent to search for relevant documents.

    Args:
        query: User's search query
        limit: Maximum number of results to return

    Returns:
        AgentResponse with search results and metadata

    Raises:
        AgentError: If agent call fails

    Example:
        >>> response = await call_retrieval_agent("Who is Aragorn?")
        >>> print(f"Found {len(response.sources)} sources")
    """
    # Implementation here
    pass
```

---

## Common Issues & Solutions

### Issue: Ollama Not Running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start Ollama
# Windows: Start from Start Menu
# Mac/Linux: ollama serve
```

### Issue: Model Not Found
```bash
# Pull required models
ollama pull llama3.2:latest
ollama pull qwen2.5:latest
ollama pull mistral:7b
ollama pull nomic-embed-text
```

### Issue: FastAgent Not Installed
```bash
# Install with uv (preferred)
uv pip install fast-agent-mcp>=0.3.17

# Or with pip
pip install fast-agent-mcp>=0.3.17
```

### Issue: Import Errors
```bash
# Ensure you're in project root
cd /path/to/buddharauer

# Ensure Python path is correct
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
# Windows: set PYTHONPATH=%PYTHONPATH%;%CD%
```

---

## Testing Strategy for Phase 3

### 1. Unit Tests
```python
# tests/unit/test_retrieval_agent.py
async def test_retrieval_agent_initialization():
    """Test agent initializes with correct config."""

async def test_retrieval_agent_search():
    """Test agent can search vector store."""

async def test_query_reformulation():
    """Test agent reformulates queries correctly."""
```

### 2. Integration Tests
```python
# tests/integration/test_fastagent_integration.py
async def test_orchestrator_routes_to_retrieval():
    """Test orchestrator correctly routes to retrieval agent."""

async def test_end_to_end_chat_flow():
    """Test complete chat flow with FastAgent."""
```

### 3. Mock Strategy
- Mock Ollama API responses for fast tests
- Use real Ollama for integration tests (if available)
- Mock vector store for agent tests
- Use TestClient for API tests

---

## Success Criteria for Phase 3

### Must Have (MVP)
- ✅ FastAgent configured with Ollama
- ✅ Retrieval agent working
- ✅ Orchestrator agent routing
- ✅ Chat endpoint using orchestrator
- ✅ Tests updated and passing

### Should Have
- ✅ Analyst agent implemented
- ✅ Web search agent implemented
- ✅ Multi-turn conversation support
- ✅ Query reformulation

### Nice to Have
- ⏸️ Streaming responses
- ⏸️ Advanced routing logic
- ⏸️ Agent performance metrics
- ⏸️ Agent A/B testing

---

## GitHub Issues

### Current
- ✅ #22 - Phase 2: Complete FastAPI Backend Integration (CLOSED)

### Next
- ⏳ #23 - Phase 3: Implement FastAgent Agents with Ollama

### Upcoming
- ⏸️ Phase 4: Gradio Frontend
- ⏸️ Phase 5: Testing & Quality
- ⏸️ Phase 6: Documentation & Deployment

---

## Resources

### Documentation
- **FastAgent Docs**: https://fast-agent.ai/
- **Ollama Docs**: https://github.com/ollama/ollama
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **ChromaDB Docs**: https://docs.trychroma.com/

### Project Docs
- `CLAUDE.md` - Project overview
- `specs/ARCHITECTURE_V2.md` - Architecture details
- `specs/IMPLEMENTATION_PLAN.md` - Development roadmap
- `SESSION_7_SUMMARY.md` - Latest session summary

---

## Estimated Timeline

### Phase 3: FastAgent Integration (1-2 weeks)
- **Days 1-2**: FastAgent setup and testing
- **Days 3-5**: Retrieval agent implementation
- **Days 6-8**: Orchestrator agent implementation
- **Days 9-10**: Integration and testing
- **Days 11-12**: Analyst and Web Search agents
- **Days 13-14**: Polish and documentation

### Phase 4: Gradio Frontend (1 week)
### Phase 5: Testing & Quality (1 week)
### Phase 6: Documentation (3-4 days)

**Total MVP Timeline**: ~6 weeks (4 weeks remaining)

---

## Quick Start Commands for Next Session

```bash
# 1. Check environment
ollama list
python --version  # Should be 3.13.5+
pip list | grep fast-agent-mcp

# 2. Run tests to ensure Phase 2 still works
pytest tests/integration/ -v --no-cov

# 3. Review key files
cat SESSION_7_SUMMARY.md
cat CLAUDE.md
cat specs/IMPLEMENTATION_PLAN.md

# 4. Start development server
uvicorn src.api.main:app --reload --port 8000

# 5. Check API docs
# Open: http://localhost:8000/docs

# 6. Start Phase 3 implementation
# See Priority 1 above
```

---

**Status**: Ready for Phase 3! 🚀
**Next**: FastAgent + Ollama Integration
**Estimated Time**: 1-2 weeks

---

*Last Updated: 2025-11-11*
*Session: 7 → 8 Transition*
