# Data Processing Pipeline Specification

## Overview
The data processing pipeline transforms raw PDF files into searchable, analyzable content stored in a vector database with associated metadata.

## Pipeline Stages

### Stage 1: PDF Text Extraction

**Input**: PDF files in `data/` directory

**Process**:
1. Scan `data/` directory for new PDF files
2. Extract text content using PyMuPDF or pdfplumber
3. Preserve document structure (pages, paragraphs)
4. Extract metadata (title, author, creation date, page count)
5. Save raw text to `processed/text/{filename}.txt`

**Output**:
- Text file: `processed/text/{filename}.txt`
- Metadata JSON: `processed/metadata/{filename}.json`

**Error Handling**:
- Corrupted PDFs: Log error, skip file, notify admin
- Encrypted PDFs: Attempt common passwords, or skip with notification
- Image-only PDFs: Flag for OCR processing (future enhancement)

---

### Stage 2: Text Processing & Cleanup

**Input**: Raw text files from Stage 1

**Process**:
1. Clean extracted text:
   - Remove excessive whitespace
   - Fix line breaks and hyphenation
   - Normalize unicode characters
   - Remove headers/footers if present
2. Detect document structure:
   - Identify chapters, sections, paragraphs
   - Detect lists, quotes, dialogue
3. Apply text preprocessing:
   - Tokenization
   - Sentence boundary detection
4. Save processed text

**Output**:
- Processed text file: `processed/text/{filename}_processed.txt`
- Structure metadata added to JSON

**Quality Checks**:
- Minimum text length validation
- Character encoding verification
- Structure detection confidence score

---

### Stage 3: Markdown Conversion

**Input**: Processed text files

**Process**:
1. Convert structured text to markdown:
   - Headings: `#`, `##`, `###` based on hierarchy
   - Paragraphs: Standard markdown formatting
   - Lists: `-` or `1.` notation
   - Emphasis: `*italic*`, `**bold**`
   - Quotes: `>` block quotes
2. Add document metadata header:
   ```markdown
   ---
   title: Document Title
   source: original_filename.pdf
   processed: 2025-01-15
   ---
   ```
3. Preserve page references for citation

**Output**:
- Markdown file: `processed/markdown/{filename}.md`

**Validation**:
- Markdown syntax verification
- Link integrity checks
- Metadata completeness

---

### Stage 4: Document Chunking

**Input**: Markdown files

**Process**:
1. Split document into semantic chunks:
   - Strategy: Sliding window with overlap
   - Chunk size: 500-1000 tokens (configurable)
   - Overlap: 100-200 tokens
   - Preserve sentence boundaries
2. Smart chunking considerations:
   - Don't split mid-sentence
   - Keep related paragraphs together
   - Respect section boundaries when possible
3. Assign chunk metadata:
   - Document ID
   - Chunk number
   - Page reference(s)
   - Section/chapter context
4. Generate chunk embeddings

**Output**:
- Chunk objects with:
  - chunk_id: unique identifier
  - document_id: source document
  - content: chunk text
  - metadata: page, section, position
  - embedding: vector representation

**Parameters** (configurable in `config.py`):
```python
CHUNK_SIZE = 800  # tokens
CHUNK_OVERLAP = 150  # tokens
MIN_CHUNK_SIZE = 100  # minimum viable chunk
MAX_CHUNK_SIZE = 1500  # maximum chunk size
```

---

### Stage 5: Embedding Generation

**Input**: Document chunks

**Process**:
1. Generate embeddings using chosen model:
   - Option A: OpenAI `text-embedding-3-small` or `text-embedding-3-large`
   - Option B: Anthropic embeddings (if available)
   - Option C: Open source (sentence-transformers)
2. Batch processing for efficiency:
   - Process chunks in batches of 100
   - Implement retry logic for API failures
   - Cache embeddings to avoid regeneration
3. Quality validation:
   - Verify embedding dimensions
   - Check for NaN/infinity values
   - Validate embedding norm

**Output**:
- Embedding vectors (typically 768 or 1536 dimensions)
- Associated with chunk IDs

**Performance**:
- Batch size: 100 chunks
- Parallel requests: 5 concurrent
- Rate limiting: Respect API limits
- Estimated time: ~1-2 seconds per 10 chunks

---

### Stage 6: Vector Database Storage

**Input**: Chunks with embeddings and metadata

**Process**:
1. Connect to vector database
2. Create collection (if not exists):
   - Collection name: `buddharauer_documents`
   - Dimensions: Match embedding model
   - Distance metric: Cosine similarity
3. Upsert chunks:
   - Store embedding vector
   - Store chunk text
   - Store metadata (document_id, page, section, etc.)
   - Create index for efficient search
4. Update document registry:
   - Track processed documents
   - Store processing timestamps
   - Link chunks to source documents

**Output**:
- Vector database populated with searchable embeddings
- Document registry updated

**Schema Example** (ChromaDB):
```python
{
    "ids": ["chunk_001", "chunk_002", ...],
    "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...], ...],
    "metadatas": [
        {
            "document_id": "doc_001",
            "filename": "example.pdf",
            "page": 1,
            "section": "Introduction",
            "chunk_index": 0,
            "processed_date": "2025-01-15"
        },
        ...
    ],
    "documents": ["chunk text content", ...]
}
```

---

### Stage 7: Entity Extraction (Optional/Advanced)

**Input**: Processed markdown documents

**Process**:
1. Extract entities using FastAgent + LLM:
   - **Characters**: Names, descriptions, attributes (gender, role, etc.)
   - **Locations**: Places, settings, geographic references
   - **Items**: Objects, artifacts, significant items
   - **Events**: Key story events, timeline markers
2. Entity schema validation:
   - Ensure required fields present
   - Validate entity types
   - Check for duplicates
3. Relationship extraction:
   - Character-to-character relationships
   - Character-to-location associations
   - Item-to-character ownership
4. Store in structured format (JSON/SQLite)

**Output**:
- Entity database: `processed/entities.json` or SQLite
- Entity graph relationships

**Entity Schema Examples**:
```python
# Character
{
    "id": "char_001",
    "name": "Aragorn",
    "type": "character",
    "attributes": {
        "gender": "male",
        "role": "ranger",
        "species": "human"
    },
    "locations": ["Bree", "Rivendell"],
    "source_documents": ["doc_001", "doc_003"],
    "mentions": 47
}

# Location
{
    "id": "loc_001",
    "name": "Bree",
    "type": "location",
    "attributes": {
        "region": "Eriador",
        "type": "town"
    },
    "characters": ["char_001", "char_023"],
    "source_documents": ["doc_001"],
    "mentions": 12
}
```

---

## Pipeline Execution

### Initial Batch Processing
```python
# Pseudocode
for pdf in get_pdfs_in_data_directory():
    if not is_processed(pdf):
        text, metadata = extract_pdf(pdf)
        processed_text = process_text(text)
        markdown = convert_to_markdown(processed_text)
        chunks = chunk_document(markdown)
        embeddings = generate_embeddings(chunks)
        store_in_vector_db(chunks, embeddings, metadata)
        extract_entities(markdown)  # optional
        mark_as_processed(pdf)
```

### Incremental Processing (Watch Mode)
```python
# Watch data/ directory for new PDFs
watch_directory("data/")
on_new_file(pdf):
    process_pipeline(pdf)
```

### Reprocessing
```python
# Force reprocess existing documents
for pdf in get_all_pdfs():
    delete_from_vector_db(pdf)
    process_pipeline(pdf)
```

## Configuration

All pipeline parameters should be configurable via `src/utils/config.py`:

```python
# config.py
PIPELINE_CONFIG = {
    "pdf_extractor": "pymupdf",  # or "pdfplumber"
    "chunk_size": 800,
    "chunk_overlap": 150,
    "embedding_model": "text-embedding-3-small",
    "vector_db": "chromadb",  # or "qdrant", "weaviate"
    "batch_size": 100,
    "parallel_workers": 5,
    "enable_entity_extraction": True,
    "processing_mode": "batch"  # or "incremental"
}
```

## Error Handling & Logging

- Log all processing steps with timestamps
- Maintain processing state for resume capability
- Create error log: `processed/errors.log`
- Track failed documents for manual review
- Send notifications for critical failures

## Testing Strategy

1. **Unit tests**: Each stage independently
2. **Integration tests**: Full pipeline with sample PDFs
3. **Performance tests**: Large document processing
4. **Quality tests**: Embedding quality, entity accuracy

## Monitoring

- Track processing times per stage
- Monitor vector DB size and query performance
- Alert on pipeline failures
- Dashboard for processing status (optional Phase 2)
