# Next Session Quick Start Guide

**Last Session**: November 16, 2025 (Session 9)
**Phase**: 3 - FastAgent Agents (40% complete)
**Priority**: Complete FastAgent integration

---

## Quick Context

You just implemented the foundation for all 4 FastAgent agents! The architecture is in place, all models are downloaded, and the agents are integrated with the FastAPI backend. Now you need to complete the FastAgent integration.

**What's Done** ✅:
- All 4 agent classes implemented (Orchestrator, Retrieval, Analyst, WebSearch)
- All 4 Ollama models downloaded (llama3.2, qwen2.5, mistral:7b, nomic-embed-text)
- Chat endpoint integrated with orchestrator (with Phase 2 fallback)
- Agent initialization in API startup
- Comprehensive documentation and type hints

**What's Next** 🚧:
- Complete FastAgent Agent instantiation (replace TODO comments)
- Implement MCP tools for vector DB and web search
- Write unit tests for agents
- Integration testing with Ollama models

---

## Immediate Next Steps (Priority Order)

### 1. Complete FastAgent Integration (High Priority)

**Files to modify** (look for `TODO` comments):
- `src/agents/orchestrator.py` - Lines ~160-165
- `src/agents/retrieval.py` - Lines ~135-140
- `src/agents/analyst.py` - Lines ~175-180
- `src/agents/web_search.py` - Lines ~155-160

**What to do**:
Replace placeholder comments with actual FastAgent Agent instantiation:

```python
# Example for orchestrator.py
from fastagent import Agent

self.agent = Agent(
    name="orchestrator",
    model=self.model,  # "generic.llama3.2:latest"
    system_prompt=system_prompt,
    tools=[retrieval_tool, analyst_tool, web_search_tool],
    temperature=self.temperature
)
```

**Resources**:
- FastAgent docs: https://docs.fast-agent.ai/
- Ollama connection already configured in `src/utils/fastagent_client.py`
- Environment variables set: `GENERIC_API_KEY=ollama`, `GENERIC_BASE_URL=http://localhost:11434/v1`

### 2. Implement MCP Tools (High Priority)

**Create new file**: `src/agents/tools/__init__.py`

**MCP Tools needed**:

#### Vector DB Tool (for Retrieval Agent)
```python
@tool
def search_vector_db(query: str, limit: int = 5) -> List[Dict]:
    """Search the vector database for relevant chunks."""
    # Use self.vector_store.search()
    # Return results with metadata
```

#### Web Search Tool (for WebSearch Agent)
```python
@tool
def search_web(query: str) -> List[Dict]:
    """Search the web using DuckDuckGo or Brave."""
    # Integrate with MCP web search server
    # Or use direct API calls for MVP
```

**Resources**:
- MCP tool docs: https://docs.fast-agent.ai/mcp/
- DuckDuckGo API: https://duckduckgo.com/api (no key needed)
- Brave Search API: https://brave.com/search/api/

### 3. Write Unit Tests (High Priority)

**Create new files**:
- `tests/unit/test_orchestrator_agent.py`
- `tests/unit/test_analyst_agent.py`
- `tests/unit/test_web_search_agent.py`

**Test coverage needed**:
- Intent classification in orchestrator
- Analysis type classification in analyst
- Query optimization in web search
- Conversation history management
- Error handling and fallbacks

**Example test structure**:
```python
import pytest
from src.agents import OrchestratorAgent

@pytest.mark.asyncio
async def test_orchestrator_intent_classification():
    orchestrator = OrchestratorAgent()

    # Test question intent
    intent = orchestrator._classify_intent("Who is Aragorn?")
    assert intent == IntentType.QUESTION

    # Test summary intent
    intent = orchestrator._classify_intent("Summarize the Ring of Power")
    assert intent == IntentType.SUMMARY
```

### 4. Integration Testing (Medium Priority)

**Test scenarios**:
1. Orchestrator → Retrieval → Response with sources
2. Orchestrator → Analyst → Structured analysis
3. Orchestrator → WebSearch → Web results summary
4. Multi-agent: Retrieval + Analyst for summary questions

**Create**: `tests/integration/test_agent_workflows.py`

---

## Current Architecture

```
User Query → FastAPI (chat endpoint)
                ↓
         Orchestrator Agent (llama3.2)
         - Intent: QUESTION
                ↓
         Retrieval Agent (qwen2.5)
         - Vector search
         - Re-rank results
                ↓
         Response with sources
```

**Fallback Flow**:
- If orchestrator fails → Phase 2 direct vector search
- If sub-agent fails → Orchestrator continues with available agents
- API always responds (graceful degradation)

---

## Key Files to Know

### Agent Implementations
- [src/agents/orchestrator.py](src/agents/orchestrator.py) - Main routing agent (610 lines)
- [src/agents/retrieval.py](src/agents/retrieval.py) - RAG agent (461 lines)
- [src/agents/analyst.py](src/agents/analyst.py) - Analysis agent (508 lines)
- [src/agents/web_search.py](src/agents/web_search.py) - Search agent (456 lines)

### Integration Points
- [src/api/routes/chat.py](src/api/routes/chat.py) - Chat endpoint with orchestrator
- [src/api/main.py](src/api/main.py) - Agent initialization on startup
- [src/agents/__init__.py](src/agents/__init__.py) - Agent exports

### Utilities
- [src/utils/fastagent_client.py](src/utils/fastagent_client.py) - FastAgent setup
- [src/database/vector_store.py](src/database/vector_store.py) - Vector DB interface
- [src/database/query_logger.py](src/database/query_logger.py) - Query tracking

---

## Quick Commands

```bash
# Check Ollama models
ollama list

# Test Ollama connectivity
curl http://localhost:11434/v1/models

# Run FastAPI server
uvicorn src.api.main:app --reload --port 8000

# Run specific tests
python -m pytest tests/unit/test_retrieval_agent.py -v

# Check test coverage
python -m pytest --cov=src/agents --cov-report=html

# View API docs
# http://localhost:8000/docs
```

---

## Common Issues & Solutions

### Issue: FastAgent import error
**Solution**: Check Python version (need 3.13.5+)
```bash
python --version
pip install fast-agent-mcp>=0.3.17
```

### Issue: Ollama connection failed
**Solution**: Start Ollama service
```bash
# Windows
ollama serve

# Check status
curl http://localhost:11434/api/tags
```

### Issue: Models not found
**Solution**: Pull missing models
```bash
ollama pull llama3.2:latest
ollama pull qwen2.5:latest
ollama pull mistral:7b
ollama pull nomic-embed-text
```

### Issue: Agent initialization fails
**Solution**: Check logs in API startup
```bash
# Look for agent initialization errors
uvicorn src.api.main:app --reload --log-level debug
```

---

## Testing Strategy

### Unit Tests (Focus First)
1. Test each agent's core methods independently
2. Mock external dependencies (vector store, Ollama API)
3. Test error handling and edge cases
4. Aim for 80%+ coverage

### Integration Tests (After Unit Tests)
1. Test agent coordination (orchestrator → sub-agents)
2. Test with real vector store (test data)
3. Mock Ollama responses for consistency
4. Test end-to-end chat flows

### Manual Testing (Final Validation)
1. Start API server
2. Use Swagger UI (http://localhost:8000/docs)
3. Send test queries via chat endpoint
4. Verify responses and sources

---

## Documentation References

- **Project Overview**: [CLAUDE.md](CLAUDE.md)
- **Architecture Details**: [specs/ARCHITECTURE_V2.md](specs/ARCHITECTURE_V2.md)
- **Implementation Plan**: [specs/IMPLEMENTATION_PLAN.md](specs/IMPLEMENTATION_PLAN.md)
- **Current Status**: [STATUS.md](STATUS.md)
- **GitHub Issue**: [#23 - Phase 3 Implementation](https://github.com/cdolan24/buddharauer/issues/23)

---

## Success Criteria for Next Session

✅ **Minimum (1-2 hours)**:
- Complete FastAgent Agent instantiation in all 4 agents
- Test basic orchestrator routing
- At least 1 MCP tool implemented (vector DB or web search)

✅ **Target (2-4 hours)**:
- All TODO comments replaced with working code
- Both MCP tools implemented
- Basic unit tests for orchestrator and retrieval
- Integration test for orchestrator → retrieval flow

✅ **Stretch (4+ hours)**:
- Complete unit test suite for all agents
- Full integration test coverage
- Manual testing with various query types
- Documentation updates

---

## Quick Debugging Tips

1. **Check agent initialization**:
   ```python
   # In API logs, look for:
   # "✓ Retrieval agent initialized"
   # "✓ Analyst agent initialized"
   # "✓ Web search agent initialized"
   # "✓ Orchestrator agent initialized"
   ```

2. **Test orchestrator directly**:
   ```python
   from src.agents import OrchestratorAgent
   orchestrator = OrchestratorAgent()
   await orchestrator.initialize()
   response = await orchestrator.process("Who is Aragorn?")
   print(response)
   ```

3. **Check Ollama model loading**:
   ```bash
   ollama ps  # Shows loaded models
   ```

4. **Verify FastAgent config**:
   ```python
   from src.utils.fastagent_client import initialize_fastagent
   config = initialize_fastagent()
   print(config)  # Should show Ollama base URL
   ```

---

**Good luck! The foundation is solid - you're 40% done with Phase 3! 🚀**

*Last updated: November 16, 2025*
