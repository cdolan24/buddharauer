#!/usr/bin/env python3
"""
Create GitHub Issues for Phase 1 Document Processing Pipeline

This script creates GitHub issues for Phase 1 priorities using the GitHub REST API.

Usage:
    python scripts/create_phase1_issues.py

Requirements:
    - requests library: pip install requests
    - GitHub Personal Access Token with repo scope
    - Set GITHUB_TOKEN environment variable
"""

import os
import sys
import requests

# GitHub repository information
GITHUB_OWNER = "cdolan24"
GITHUB_REPO = "buddharauer"
GITHUB_API_URL = "https://api.github.com"

def get_github_token() -> str:
    """Get GitHub token from environment variable."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ ERROR: GITHUB_TOKEN environment variable not set")
        print("\nTo create a GitHub token:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Click 'Generate new token (classic)'")
        print("3. Select 'repo' scope")
        print("4. Copy the token and set: export GITHUB_TOKEN=your_token_here")
        sys.exit(1)
    return token

def create_issue(token: str, title: str, body: str) -> dict:
    """Create a GitHub issue."""
    url = f"{GITHUB_API_URL}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": title,
        "body": body,
        "labels": ["phase-1", "priority"]
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# Define Phase 1 priority issues
ISSUES = [
    {
        "title": "Implement Chunking Integration Pipeline",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Component**: Chunking Integration

**Description**:
Implement the chunking integration pipeline to connect PDF extraction with semantic chunking.

**Tasks**:
- [ ] Create ChunkingPipeline class
- [ ] Implement semantic chunk size optimization
- [ ] Add metadata preservation logic
- [ ] Add progress tracking integration
- [ ] Write integration tests with PDF extractor

**Technical Details**:
- Build on top of existing PDF extractor improvements
- Ensure metadata is preserved through the pipeline
- Add configurable chunk size optimization
- Implement progress tracking
- Add comprehensive tests

**Definition of Done**:
1. ChunkingPipeline class implemented and tested
2. Integration tests with PDF extractor passing
3. Chunk size optimization working
4. Metadata preservation verified
5. Progress tracking functional

**Dependencies**:
- PDF Extractor module
- Current test coverage maintained"""
    },
    {
        "title": "Implement Pipeline Orchestration System",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Component**: Pipeline Orchestration

**Description**:
Create the main pipeline orchestration system to manage the document processing workflow.

**Tasks**:
- [ ] Create DocumentPipeline class
- [ ] Implement pipeline state management
- [ ] Add progress tracking aggregation
- [ ] Add error recovery for partial failures
- [ ] Add state persistence and resumption
- [ ] Write end-to-end tests

**Technical Details**:
- Create main pipeline coordinator
- Implement state management
- Add progress tracking across components
- Add error recovery mechanisms
- Implement state persistence
- Add comprehensive testing

**Definition of Done**:
1. DocumentPipeline class implemented
2. State management working
3. Progress tracking functional
4. Error recovery tested
5. End-to-end tests passing

**Dependencies**:
- All pipeline components
- State persistence system"""
    },
    {
        "title": "Implement Vector Store Integration",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: Medium
**Component**: Vector Store Integration

**Description**:
Implement vector store integration with chunking output and optimize for performance.

**Tasks**:
- [ ] Create VectorStorePipeline class
- [ ] Implement optimized bulk insertion
- [ ] Add metadata filtering system
- [ ] Add chunk deduplication
- [ ] Write integration tests

**Technical Details**:
- Integrate with ChromaDB
- Optimize bulk operations
- Implement metadata system
- Add deduplication logic
- Add comprehensive tests

**Definition of Done**:
1. VectorStorePipeline implemented
2. Bulk operations optimized
3. Metadata filtering working
4. Deduplication tested
5. Integration tests passing

**Dependencies**:
- Chunking pipeline
- ChromaDB setup"""
    }
- [ ] Handle special cases (tables, lists)
- [ ] Write unit tests

**Technical Details**:
- Use LangChain for semantic chunking
- Configurable chunk sizes and overlap
- Preserve document structure
- Handle edge cases properly

**Testing**:
- [ ] Test chunk size configurations
- [ ] Verify metadata preservation
- [ ] Test special case handling
- [ ] Validate chunk coherence
"""
    },
    {
        "title": "Implement Embedding Generation Module",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Component**: Embedding Generation

**Description**:
Develop the embedding generation module using Ollama's nomic-embed-text model.

**Tasks**:
- [ ] Create `src/pipeline/embeddings.py`
- [ ] Integrate Ollama embeddings (nomic-embed-text)
- [ ] Implement batch processing
- [ ] Add progress tracking
- [ ] Implement error handling
- [ ] Write unit tests

**Technical Details**:
- Use nomic-embed-text model via Ollama
- Implement efficient batch processing
- Track progress for large documents
- Handle API errors gracefully

**Testing**:
- [ ] Test embedding generation
- [ ] Verify batch processing
- [ ] Test progress tracking
- [ ] Validate error handling
"""
    }
]

def main():
    """Create all Phase 1 priority issues."""
    token = get_github_token()
    
    print("Creating Phase 1 priority issues...")
    for issue in ISSUES:
        try:
            response = create_issue(token, issue["title"], issue["body"])
            print(f"✅ Created issue: {response['html_url']}")
        except Exception as e:
            print(f"❌ Error creating issue '{issue['title']}': {str(e)}")
    
    print("\nDone! Check your GitHub repository for the new issues.")

if __name__ == "__main__":
    main()