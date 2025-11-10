# Buddharauer Specifications

This directory contains detailed specifications and planning documents for the Buddharauer project.

## Documents

### [architecture.md](architecture.md)
Complete system architecture including:
- Technology stack decisions
- High-level component design
- Directory structure
- Data flow diagrams
- Agent design patterns
- Scalability considerations

**Read this first** to understand the overall system design.

### [data-processing-pipeline.md](data-processing-pipeline.md)
Detailed pipeline specification covering:
- All 7 stages from PDF to vector database
- Input/output for each stage
- Error handling strategies
- Configuration parameters
- Schema examples
- Testing approach

**Essential for implementing** the document processing system.

### [user-stories-detailed.md](user-stories-detailed.md)
Comprehensive user requirements including:
- Detailed acceptance criteria
- Example interactions
- Technical requirements
- Admin functionality
- Future enhancements

**Read this** to understand user needs and expected behavior.

### [implementation-phases.md](implementation-phases.md)
Development roadmap with:
- 10 phases from setup to production
- Task breakdowns for each phase
- Deliverables and testing strategies
- Timeline estimates (11 weeks MVP)
- Risk management
- Success metrics

**Follow this** for structured implementation approach.

## Reading Order for Implementation

1. **architecture.md** - Understand the big picture
2. **user-stories-detailed.md** - Know what you're building
3. **implementation-phases.md** - Plan your work
4. **data-processing-pipeline.md** - Implement the core functionality

## Key Decisions Made

### Technology Choices
- **FastAgent**: MCP-native framework, good documentation, active development
- **ChromaDB**: Start simple, migrate to Qdrant for production
- **PyMuPDF**: Fast and reliable for text extraction
- **Anthropic Claude**: Best reasoning for complex entity extraction

### Architecture Decisions
- **Pipeline-based processing**: Clear separation of concerns
- **Vector database for search**: Semantic search over keyword matching
- **Agent-based design**: Specialized agents for different tasks (QA, summarization, etc.)
- **CLI first**: Simple interface before web complexity

### Data Decisions
- **Chunking strategy**: 800 tokens with 150 overlap (balances context and retrieval)
- **Entity storage**: JSON for simplicity, SQLite for relationships
- **Metadata tracking**: Separate metadata files for each document
- **Citation system**: Track page numbers for all chunks

## Implementation Strategy

**Start small, expand gradually:**
1. Get ONE PDF working end-to-end
2. Add support for multiple PDFs
3. Enhance with entity extraction
4. Add advanced features

**Testing throughout:**
- Unit tests for each component
- Integration tests for workflows
- Performance benchmarks
- Quality validation

## Questions to Resolve During Implementation

1. **Embedding model**: OpenAI vs open source (cost vs control)
2. **Entity extraction approach**: Pure LLM vs hybrid with NER libraries
3. **Relationship storage**: Graph database vs JSON vs SQLite
4. **Web interface**: FastAPI + React vs Streamlit (Phase 11)
5. **OCR integration**: When to add for image-based PDFs

## Notes for Developers

- Refer back to these specs when implementing features
- Update specs if requirements change
- Add learnings and gotchas to CLAUDE.md
- Keep specs synchronized with actual implementation

## Version History

- v1.0 (2025-11-05): Initial specifications created during planning phase
