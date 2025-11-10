# Error Recovery System Documentation

## Overview

The error recovery system provides robust error handling and recovery capabilities for the document processing pipeline. It ensures that operations can be resumed after failures and prevents data loss during processing.

## Components

### 1. RecoveryManager (`src/pipeline/recovery.py`)

#### Purpose
- Manages operation state persistence
- Tracks active operations
- Handles recovery of incomplete operations
- Provides cleanup of completed operations

#### Key Features
```python
class RecoveryManager:
    def start_operation(operation_type: str, input_data: Dict[str, Any]) -> RecoveryState:
        """Start tracking a new operation."""
        
    def update_operation(operation_id: str, status: str, error: Optional[str] = None):
        """Update operation status."""
        
    def list_incomplete_operations() -> Dict[str, RecoveryState]:
        """List operations that need recovery."""
```

### 2. Retry Mechanism

#### Purpose
- Provides automatic retry for failed operations
- Implements exponential backoff
- Prevents unnecessary retries

#### Usage
```python
@with_retry(max_retries=3, initial_delay=1.0)
async def operation():
    """Operation will be retried up to 3 times with exponential backoff."""
```

### 3. Enhanced PipelineOrchestrator

#### New Features
- Operation state tracking
- Automatic recovery of incomplete operations
- Improved error reporting
- Enhanced statistics tracking
- Duplicate processing prevention

#### Key Methods
```python
async def process_pdf(pdf_path: Path) -> bool:
    """Process PDF with recovery support."""
    
async def process_directory(dir_path: Path, recursive: bool = True) -> ProcessingStats:
    """Process directory with automatic recovery of failed operations."""
```

## Recovery Process

1. Operation Tracking
   - Each operation gets unique ID
   - State saved to disk
   - Status updates tracked

2. Failure Detection
   - Exceptions caught and logged
   - Operation marked as failed
   - Error details preserved

3. Recovery
   - Incomplete operations detected on startup
   - Automatic retry with backoff
   - Success/failure tracking

4. Cleanup
   - Successful operations cleaned up
   - Failed operations preserved
   - State files managed automatically

## Configuration

Recovery system configuration in `fastagent.config.yaml`:
```yaml
recovery:
  state_dir: "data/recovery"    # Directory for state files
  max_retries: 3               # Maximum retry attempts
  initial_delay: 1.0           # Initial retry delay (seconds)
  max_delay: 60.0             # Maximum retry delay (seconds)
```

## Testing

Comprehensive test suite in `tests/unit/test_recovery.py`:
- State serialization
- Operation tracking
- Retry mechanism
- Recovery process
- Error handling
- Duplicate prevention

## Next Steps

1. Monitoring Enhancement
   - Add detailed progress tracking
   - Implement performance monitoring
   - Create monitoring dashboard
   - Add alerting for failures

2. Pipeline Optimization
   - Optimize batch processing
   - Improve memory usage
   - Enhance concurrency
   - Add performance benchmarks

3. Additional Features
   - Add operation prioritization
   - Implement selective retry policies
   - Add operation dependencies
   - Enhanced progress reporting