# Next Session Priorities

**Last Updated**: November 10, 2025 (Session 4)
**Current Status**: Phase 2 - FastAPI Backend (85% complete)

---

## Quick Status

- ✅ **Tests**: 96/96 passing (100%)
- ⚠️ **Coverage**: 88.04% (target: 90%+)
- ✅ **Code Quality**: Excellent (no duplication)
- ✅ **Documentation**: Complete

---

## Immediate Priorities (Next Session)

### 1. 🎯 Increase Test Coverage to 90%+ (Issue #24)
**Priority**: High | **Time**: 3-4 hours

Add missing tests for error paths and edge cases:

- **embeddings.py** (79% → 90%+):
  - Test HTTP error retry logic (lines 103-106)
  - Test empty texts list (line 150)
  - Test batch error handling (lines 180-183)
  - Test error logging (lines 200-204)

- **vector_store.py** (89% → 90%+):
  - Test invalid metadata handling (lines 70-76)
  - Test empty result cases (line 152)
  - Test delete operations (lines 417-419)

- **pdf_extractor.py** (89% → 90%+):
  - Test corrupted file edge cases (lines 85, 92, 96)
  - Test large file handling (line 158)
  - Test special character handling (lines 263-268)

**Files to modify**:
- `tests/unit/test_embeddings_enhanced.py`
- `tests/unit/test_vector_store.py`
- `tests/unit/test_pdf_extractor.py`

### 2. 🚀 Start Phase 3 - FastAgent Agents (Issue #23)
**Priority**: Critical Path | **Time**: 6-8 hours

This unblocks Phase 2 API completion!

**Tasks**:
1. Setup FastAgent with Ollama
   - Configure `fastagent.config.yaml`
   - Set environment variables (GENERIC_API_KEY, GENERIC_BASE_URL)
   - Test basic connectivity

2. Implement Retrieval Agent (RAG)
   - Create `src/agents/retrieval.py`
   - MCP tool for vector DB access
   - Use `generic.qwen2.5:latest`

3. Implement Orchestrator Agent
   - Create `src/agents/orchestrator.py`
   - Use `generic.llama3.2:latest`
   - Define tools for sub-agents

**Files to create**:
- `src/agents/__init__.py`
- `src/agents/retrieval.py`
- `src/agents/orchestrator.py`
- `fastagent.config.yaml` (if not exists)

### 3. 🔧 Complete Phase 2 - FastAPI Backend (Issue #22)
**Priority**: High | **Time**: 4-5 hours
**Blocked by**: Phase 3 agents

**Tasks**:
1. Implement document registry integration
   - Create `src/database/document_registry.py`
   - SQLite database for tracking
   - CRUD operations

2. Implement vector store dependency injection
   - Update `src/api/main.py` lifespan
   - Initialize VectorStore on startup
   - Add dependency injection

3. Add query logger
   - Create `src/database/query_logger.py`
   - Log queries to SQLite
   - Track response times

4. Complete API route TODOs
   - Implement document endpoints (currently stubs)
   - Integrate with agents
   - Add comprehensive error handling

**Files to modify**:
- `src/api/main.py`
- `src/api/routes/documents.py`
- `src/api/routes/search.py`

---

## Context from Session 4

### What Was Accomplished ✅

1. **Code Quality Improvements**:
   - Created `scripts/github_utils.py` shared module (169 lines)
   - Eliminated ~150 lines of duplicate code
   - Refactored 3 scripts to use shared utilities
   - All code well-documented with type hints

2. **GitHub Issues**:
   - Created issue #24: Test coverage improvements
   - Created & closed issue #25: Completed code quality work

3. **Documentation**:
   - Updated `DEVELOPMENT_NOTES.md`
   - Updated `STATUS.md`
   - Created `SESSION_NOTES_2025-11-10_Session4.md`

4. **Git**:
   - Committed: `6739af8` (refactor: Consolidate GitHub API utilities)
   - Pushed to origin/main

### Key Files Modified
- ✅ `scripts/github_utils.py` (new)
- ✅ `scripts/create_coverage_issues.py` (new)
- ✅ `scripts/create_github_issues.py` (refactored)
- ✅ `scripts/create_embedding_issues.py` (refactored)
- ✅ `scripts/create_phase1_issues.py` (refactored)
- ✅ `DEVELOPMENT_NOTES.md` (updated)
- ✅ `STATUS.md` (updated)

---

## Important Notes

### Architecture Context
- **Hybrid Approach**: FastAgent (agents) + FastAPI (REST) + Ollama (local models)
- **Current Phase**: Phase 2 (85% complete) - blocked on Phase 3
- **Critical Path**: Phase 3 agents → Phase 2 API completion → Phase 4 UI

### Test Coverage Strategy
- Focus on error paths and edge cases
- Don't test API stubs (implement functionality first)
- Target: 90%+ overall, >85% per module
- All new tests must be reliable (no flaky tests)

### FastAgent Setup
- Requires Python 3.13.5+
- Models: llama3.2:latest, qwen2.5:latest, mistral:7b
- Endpoint: http://localhost:11434/v1
- Tool calling tested with llama3.2 and qwen2.5

### GitHub Issues
- Open: #7, #10, #11, #22, #23, #24
- Recently Closed: #25 (code quality - completed)
- Use `gh issue list` to see all open issues

---

## Quick Commands

### Run Tests
```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html

# Specific module
python -m pytest tests/unit/test_embeddings.py -v
```

### Check Status
```bash
# Git status
git status

# GitHub issues
gh issue list

# Test coverage
# Open htmlcov/index.html after running pytest with --cov-report=html
```

### Create Issues
```bash
# Use the shared utility
python scripts/create_coverage_issues.py
```

---

## Questions to Consider

1. **FastAgent Setup**: Is Ollama running? Models pulled?
2. **Configuration**: Is fastagent.config.yaml created?
3. **Dependencies**: Are all Phase 3 dependencies installed?
4. **Testing Strategy**: Should we test agents before integration?

---

## Resources

- [CLAUDE.md](CLAUDE.md) - Project overview
- [ARCHITECTURE_V2.md](specs/ARCHITECTURE_V2.md) - Architecture details
- [IMPLEMENTATION_PLAN.md](specs/IMPLEMENTATION_PLAN.md) - Full plan
- [STATUS.md](STATUS.md) - Current status
- [DEVELOPMENT_NOTES.md](DEVELOPMENT_NOTES.md) - Dev patterns
- [SESSION_NOTES_2025-11-10_Session4.md](SESSION_NOTES_2025-11-10_Session4.md) - Session 4 notes

---

*This file provides quick context for starting the next session*
*Delete or archive after next session completes*
