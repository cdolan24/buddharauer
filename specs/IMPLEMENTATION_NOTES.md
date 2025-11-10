# Implementation Notes for Future Sessions

## Session History

### Session 1: Planning & Documentation (2025-11-05)
**Status**: Planning phase completed ✅

**What was accomplished**:
- Researched FastAgent framework (fast-agent-mcp v0.3.17+)
- Created comprehensive architecture documentation
- Designed 7-stage data processing pipeline
- Documented detailed user stories with acceptance criteria
- Created 11-week implementation roadmap (10 phases)
- Updated README with full project overview and suggestions
- Updated CLAUDE.md with complete context for future sessions
- Created .env.example and .gitignore
- Created specs directory with 4 detailed specification documents

**Files created**:
- `specs/architecture.md` - System architecture and design
- `specs/data-processing-pipeline.md` - Pipeline specification
- `specs/user-stories-detailed.md` - Requirements and use cases
- `specs/implementation-phases.md` - Development roadmap
- `specs/README.md` - Specs directory guide
- `.env.example` - Configuration template
- `.gitignore` - Comprehensive ignore rules

**Files updated**:
- `README.md` - Complete project overview with implementation suggestions
- `CLAUDE.md` - Full context for AI assistants

---

## Next Session: Phase 0 - Project Setup

### Prerequisites
Before starting implementation, ensure:
1. Python 3.13.5+ is installed
2. uv package manager is installed
3. You have API keys ready:
   - Anthropic API key (for Claude)
   - OpenAI API key (for embeddings)

### First Steps for Implementation

#### 1. Create Directory Structure
```bash
mkdir -p data
mkdir -p processed/{text,markdown,metadata}
mkdir -p src/{agents,pipeline,database,models,client,utils}
mkdir -p tests
```

#### 2. Initialize Python Project
Create `pyproject.toml` with project configuration:
- Project name: buddharauer
- Python version: >=3.13.5, <3.14
- Dependencies: fast-agent-mcp, chromadb, pymupdf, pytest

#### 3. Install Core Dependencies
```bash
uv pip install fast-agent-mcp
uv pip install chromadb
uv pip install pymupdf
uv pip install pytest pytest-asyncio pytest-cov
uv pip install python-dotenv  # For .env file support
```

#### 4. Initialize FastAgent
```bash
fast-agent setup
```
This will create example agent and config files. Review these examples to understand FastAgent patterns.

#### 5. Create Configuration Module
Start with `src/utils/config.py`:
- Load environment variables from .env
- Define all configuration parameters (chunk size, overlap, etc.)
- Validate required API keys are present

#### 6. Set Up Logging
Create `src/utils/logging.py`:
- Configure logging format and level
- Set up file logging to buddharauer.log
- Create logger factory function

#### 7. Create .env File
```bash
cp .env.example .env
# Edit .env and add your API keys
```

#### 8. Add Sample PDF
Place at least one test PDF in the `data/` directory for testing.

---

## Key Decisions & Rationale

### Technology Choices Made

1. **FastAgent (fast-agent-mcp)**
   - Reason: MCP-native, well-documented, active development
   - Supports Anthropic, OpenAI, Google providers
   - Built-in support for structured outputs and PDF handling
   - Version: 0.3.17+ (requires Python 3.13.5+)

2. **ChromaDB for MVP**
   - Reason: Easy setup, Python-native, good for prototyping
   - Plan to migrate to Qdrant for production scale
   - Lightweight with minimal dependencies

3. **PyMuPDF (fitz) for PDF Processing**
   - Reason: Fast and reliable text extraction
   - Alternative: pdfplumber for tables (consider for Phase 1)

4. **Anthropic Claude for LLM**
   - Reason: Best reasoning capabilities for entity extraction
   - Good for complex tasks like relationship detection

5. **OpenAI for Embeddings**
   - Model: text-embedding-3-small (cost-effective)
   - Dimensions: 1536
   - Alternative: sentence-transformers for open-source option

### Architecture Decisions Made

1. **Pipeline-Based Processing**
   - Clear separation of concerns
   - Easy to test individual stages
   - Enables incremental processing

2. **Agent-Based Design**
   - Specialized agents for different tasks
   - QA, Summarization, Categorization, Extraction agents
   - Follows FastAgent patterns

3. **Vector Database for Search**
   - Semantic search over keyword matching
   - Better for natural language queries
   - Supports similarity-based retrieval

4. **CLI First Approach**
   - Simpler to implement than web interface
   - FastAgent has built-in CLI support
   - Web interface can be added later (Phase 11)

5. **JSON for Entity Storage (MVP)**
   - Simple to implement
   - Easy to inspect and debug
   - Can migrate to SQLite for relationships later

### Data Processing Decisions

1. **Chunking Strategy**
   - Chunk size: 800 tokens (sweet spot for context vs retrieval)
   - Overlap: 150 tokens (ensures continuity)
   - Adjustable via config (500-1000 range)

2. **Metadata Tracking**
   - Separate JSON file per document
   - Tracks: filename, page count, processing date, source info
   - Enables citation system

3. **Entity Schema Design**
   - Characters: name, gender, role, species, locations, mentions
   - Locations: name, region, type, characters, mentions
   - Items: name, type, owner, location, mentions
   - Extensible schema for future entity types

---

## Implementation Strategy

### Guiding Principles

1. **Start Small, Expand Gradually**
   - Get ONE PDF working end-to-end first
   - Validate approach before scaling
   - Iterate on quality before quantity

2. **Test Throughout**
   - Unit tests for each component
   - Integration tests for workflows
   - Performance benchmarks early
   - Target: >80% coverage

3. **Configuration-Driven**
   - All parameters in config.py
   - Environment-specific settings in .env
   - Easy to tune without code changes

4. **Error Handling from Start**
   - Graceful degradation for bad PDFs
   - Retry logic for API failures
   - Comprehensive logging
   - User-friendly error messages

### Implementation Order

**Phase 0: Project Setup** (Week 1) ⬅️ START HERE
- Setup environment and dependencies
- Create directory structure
- Initialize configuration system
- Set up logging
- Create initial tests

**Phase 1: PDF Processing Pipeline** (Week 2-3)
- PDF text extraction
- Text cleanup and processing
- Markdown conversion
- Metadata extraction
- Batch processing script

**Phase 2: Vector Database Integration** (Week 3-4)
- ChromaDB setup
- Chunking implementation
- Embedding generation
- Vector storage
- Query interface

**Phase 3: FastAgent Basic QA** (Week 4-5)
- First agent: QA agent
- RAG implementation
- Citation system
- CLI interface
- Conversation history

**Phases 4-10**: See specs/implementation-phases.md

---

## Open Questions to Resolve During Implementation

### Phase 1 Questions
- [ ] PyMuPDF vs pdfplumber: Test both with sample PDFs, choose based on quality
- [ ] Text cleanup strategy: How aggressive should whitespace normalization be?
- [ ] Markdown conversion: What heading levels to use for document structure?

### Phase 2 Questions
- [ ] Embedding model: OpenAI vs open-source (cost vs control tradeoff)
- [ ] Chunk overlap: 150 tokens enough? Test with queries spanning chunk boundaries
- [ ] Collection naming: Single collection or multiple (by document type)?

### Phase 3 Questions
- [ ] Citation format: "Source: doc.pdf, page 5" vs "[doc.pdf:5]" vs footnotes?
- [ ] Context window: How many chunks to retrieve per query? (start with 5)
- [ ] Conversation history: How many exchanges to maintain? (start with 5)

### Phase 4 Questions
- [ ] Entity extraction: Pure LLM vs hybrid with spaCy NER?
- [ ] Deduplication: Fuzzy matching threshold? (start with 0.9 similarity)
- [ ] Relationship storage: JSON enough or need graph database?

### Future Questions (defer to later phases)
- [ ] OCR integration: When to add for image-based PDFs? (Phase 11+)
- [ ] Web interface: FastAPI + React vs Streamlit? (Phase 11)
- [ ] Multi-language: Support non-English PDFs? (Future enhancement)

---

## Known Constraints & Limitations

### Technical Constraints
1. **FastAgent requires Python 3.13.5+**
   - Strict version requirement
   - May limit deployment environments

2. **API Costs**
   - Embedding generation: ~$0.02 per 1M tokens (text-embedding-3-small)
   - LLM calls: Variable based on provider and model
   - Mitigation: Implement caching, batch processing

3. **ChromaDB Scale Limits**
   - Good for <100K documents
   - Plan migration to Qdrant if scaling beyond MVP

4. **PDF Quality Dependency**
   - Text-based PDFs only (MVP)
   - Image/scanned PDFs need OCR (future)
   - Complex layouts may have extraction issues

### Scope Limitations (MVP)
1. **Single User**
   - No authentication or multi-user support
   - Local deployment only

2. **English Only**
   - Entity extraction prompts assume English
   - Can extend to other languages later

3. **No Real-Time Collaboration**
   - No concurrent editing of documents
   - No shared query history

4. **CLI Interface Only**
   - Web interface deferred to Phase 11
   - Mobile interface not planned

---

## Testing Strategy

### Unit Tests
- Each pipeline stage independently
- Mock API calls (embeddings, LLM)
- Test edge cases (empty PDFs, corrupted files)
- Validate schema compliance

### Integration Tests
- Full pipeline: PDF → Markdown → Vector DB
- End-to-end query flow
- Document addition/removal workflows
- Error recovery scenarios

### Performance Tests
- Large document processing (100+ pages)
- Batch processing (10+ documents)
- Query response time (<3 seconds target)
- Concurrent query handling

### Quality Tests
- Embedding quality: Semantic similarity checks
- Entity extraction accuracy: Compare with manual labels
- Citation accuracy: Verify page numbers
- Answer relevance: Use test queries with known answers

---

## Risk Management

### High-Risk Areas

1. **PDF Extraction Quality**
   - Risk: Poor text extraction from complex PDFs
   - Mitigation: Test with diverse PDF samples early, manual review process

2. **Entity Extraction Accuracy**
   - Risk: LLM hallucinations or missed entities
   - Mitigation: Schema validation, confidence scores, manual verification

3. **API Cost Overruns**
   - Risk: Expensive at scale
   - Mitigation: Cost tracking, caching, batch processing, open-source alternatives

4. **Vector Search Quality**
   - Risk: Poor retrieval of relevant chunks
   - Mitigation: Tune chunking strategy, test with real queries, adjust similarity threshold

### Monitoring & Alerts

Set up monitoring for:
- Processing failure rate (alert if >5%)
- Query response time (alert if >5 seconds)
- API costs (alert if >budget threshold)
- Vector DB size (alert if approaching limits)

---

## Success Metrics

### MVP Success Criteria (End of Phase 3)
- ✅ Process 10+ PDFs successfully
- ✅ Answer questions with >80% relevance
- ✅ Query response time <5 seconds
- ✅ Citations accurate in >95% of cases
- ✅ >80% test coverage

### Full Feature Success (End of Phase 10)
- ✅ Process 100+ PDFs without issues
- ✅ Extract entities with >85% accuracy
- ✅ Generate coherent summaries
- ✅ Support complex filtering queries
- ✅ >90% test coverage
- ✅ Complete documentation

---

## Resources & References

### Documentation
- FastAgent Docs: https://fast-agent.ai/
- FastAgent GitHub: https://github.com/evalstate/fast-agent
- ChromaDB Docs: https://docs.trychroma.com/
- PyMuPDF Docs: https://pymupdf.readthedocs.io/

### Example Implementations
- FastAgent has examples via `fast-agent setup` command
- Review FastAgent "Building Effective Agents" examples
- Study FastAgent workflow patterns

### Key Papers
- "Building Effective Agents" by Anthropic
- RAG (Retrieval-Augmented Generation) best practices

---

## Notes for Next Developer

### Quick Start for Next Session

1. **Read CLAUDE.md first** - Has all context needed
2. **Review specs/implementation-phases.md** - Follow Phase 0 tasks
3. **Start with project setup** - Don't jump to implementation yet
4. **Test with ONE PDF** - Validate approach end-to-end before scaling

### What NOT to Do

❌ Don't start coding agents before pipeline is working
❌ Don't process multiple PDFs before ONE works perfectly
❌ Don't add features beyond current phase scope
❌ Don't skip tests - write them alongside implementation
❌ Don't commit API keys or sensitive data

### What TO Do

✅ Follow the phases in order
✅ Write tests for each component
✅ Log everything for debugging
✅ Start simple, add complexity gradually
✅ Validate with real PDFs early and often
✅ Update documentation as you learn
✅ Track API costs from day one

---

## Project Status Summary

**Current State**: Planning complete, ready for implementation

**Next Action**: Begin Phase 0 - Project Setup

**Files Ready**:
- ✅ Architecture documented
- ✅ Pipeline specified
- ✅ User stories detailed
- ✅ Implementation roadmap created
- ✅ README updated
- ✅ CLAUDE.md updated
- ✅ .env.example created
- ✅ .gitignore created

**Need to Create**:
- ⏳ pyproject.toml
- ⏳ src/ directory structure
- ⏳ tests/ directory structure
- ⏳ Initial configuration module
- ⏳ Logging setup
- ⏳ First unit tests

**Timeline**: 6 weeks to MVP (matches IMPLEMENTATION_PLAN.md)

**Focus**: Start simple, validate approach, iterate on quality before scale.

---

*Last updated: 2025-11-10*
*Current Phase: Phase 1 (Document Processing Pipeline)*
*Next Steps: Improve test coverage and error handling*
