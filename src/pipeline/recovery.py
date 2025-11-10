"""
Utilities for error recovery and resilience in the pipeline.
"""
from dataclasses import dataclass
from typing import TypeVar, Callable, Any, Optional, Dict
import asyncio
import json
from pathlib import Path
import time
from functools import wraps
from datetime import datetime

from src.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

@dataclass
class RecoveryState:
    """State information for recovery."""
    operation_id: str
    start_time: float
    operation_type: str
    input_data: Dict[str, Any]
    status: str
    error: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for persistence."""
        return {
            'operation_id': self.operation_id,
            'start_time': self.start_time,
            'operation_type': self.operation_type,
            'input_data': self.input_data,
            'status': self.status,
            'error': self.error,
            'retry_count': self.retry_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecoveryState':
        """Create state from dictionary."""
        return cls(**data)


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
) -> Callable:
    """
    Decorator for retrying operations with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error = None
            delay = initial_delay
            
            for retry in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if retry == max_retries:
                        logger.error(f"Max retries ({max_retries}) reached for {func.__name__}")
                        raise
                    
                    logger.warning(
                        f"Attempt {retry + 1}/{max_retries} failed for {func.__name__}: {str(e)}"
                    )
                    
                    # Calculate next delay with exponential backoff
                    delay = min(delay * exponential_base, max_delay)
                    await asyncio.sleep(delay)
            
            raise last_error  # This should never be reached
            
        return wrapper
    return decorator


class RecoveryManager:
    """Manages recovery state and persistence for pipeline operations."""
    
    def __init__(self, state_dir: Path):
        """
        Initialize recovery manager.
        
        Args:
            state_dir: Directory for storing recovery state files
        """
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.active_operations: Dict[str, RecoveryState] = {}
        
    def start_operation(
        self,
        operation_type: str,
        input_data: Dict[str, Any]
    ) -> RecoveryState:
        """
        Start tracking a new operation for recovery.
        
        Args:
            operation_type: Type of operation being performed
            input_data: Input data for the operation
            
        Returns:
            New recovery state object
        """
        state = RecoveryState(
            operation_id=f"{operation_type}_{int(time.time())}",
            start_time=time.time(),
            operation_type=operation_type,
            input_data=input_data,
            status="started"
        )
        
        self.active_operations[state.operation_id] = state
        self._persist_state(state)
        return state
        
    def update_operation(
        self,
        operation_id: str,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """
        Update the status of an operation.
        
        Args:
            operation_id: ID of the operation to update
            status: New status
            error: Optional error message
        """
        if operation_id not in self.active_operations:
            logger.warning(f"Attempted to update unknown operation: {operation_id}")
            return
            
        state = self.active_operations[operation_id]
        state.status = status
        state.error = error
        
        if status == "completed":
            self._cleanup_operation(operation_id)
        else:
            self._persist_state(state)
            
    def _persist_state(self, state: RecoveryState) -> None:
        """Save operation state to disk."""
        state_file = self.state_dir / f"{state.operation_id}.json"
        with state_file.open('w') as f:
            json.dump(state.to_dict(), f)
            
    def _cleanup_operation(self, operation_id: str) -> None:
        """Clean up completed operation state."""
        if operation_id in self.active_operations:
            del self.active_operations[operation_id]
            
        state_file = self.state_dir / f"{operation_id}.json"
        if state_file.exists():
            state_file.unlink()
            
    def list_incomplete_operations(self) -> Dict[str, RecoveryState]:
        """List all operations that haven't completed."""
        incomplete = {}
        for state_file in self.state_dir.glob("*.json"):
            with state_file.open() as f:
                state_data = json.load(f)
                state = RecoveryState.from_dict(state_data)
                if state.status not in ["completed", "failed"]:
                    incomplete[state.operation_id] = state
        return incomplete