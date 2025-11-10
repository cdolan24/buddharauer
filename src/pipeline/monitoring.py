"""
Monitoring system for pipeline components.
Provides real-time metrics, progress tracking, and performance monitoring.
"""
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import asyncio
import json
from pathlib import Path
import logging
from contextlib import contextmanager

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"      # Incrementing values (docs processed, errors, etc)
    GAUGE = "gauge"         # Point-in-time values (memory usage, queue size)
    HISTOGRAM = "histogram" # Distribution of values (processing times)
    RATE = "rate"          # Per-second rates (throughput)


@dataclass
class Metric:
    """A single metric measurement."""
    name: str
    value: float
    type: MetricType
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ProgressInfo:
    """Progress information for long-running operations."""
    operation: str
    total_items: int
    completed_items: int
    started_at: float
    status: str
    eta: Optional[float] = None
    current_item: Optional[str] = None
    sub_operation: Optional[str] = None
    error_count: int = 0


class MonitoringSystem:
    """Central monitoring system for tracking metrics and progress."""
    
    def __init__(self, metrics_dir: Optional[Path] = None):
        """
        Initialize monitoring system.
        
        Args:
            metrics_dir: Directory for storing metrics data.
                       If None, uses data/metrics.
        """
        if metrics_dir is None:
            metrics_dir = Path("data/metrics")
        self.metrics_dir = metrics_dir
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_metrics: Dict[str, Metric] = {}
        self.progress_trackers: Dict[str, ProgressInfo] = {}
        self._operation_handlers: Dict[str, Callable] = {}
        
    def register_operation(
        self,
        operation: str,
        handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register a handler for operation events.
        
        Args:
            operation: Name of the operation
            handler: Callback function for handling events
        """
        self._operation_handlers[operation] = handler
        
    def record_metric(self, metric: Metric) -> None:
        """
        Record a new metric value.
        
        Args:
            metric: The metric to record
        """
        self.current_metrics[metric.name] = metric
        self._persist_metric(metric)
        
        # Log significant changes
        if metric.type in [MetricType.COUNTER, MetricType.GAUGE]:
            logger.debug(
                f"Metric {metric.name}: {metric.value} "
                f"[{', '.join(f'{k}={v}' for k, v in metric.labels.items())}]"
            )
        
    def update_progress(
        self,
        operation: str,
        completed: int,
        total: int,
        current_item: Optional[str] = None,
        sub_operation: Optional[str] = None,
        error_count: int = 0
    ) -> None:
        """
        Update progress for an operation.
        
        Args:
            operation: Name of the operation
            completed: Number of completed items
            total: Total number of items
            current_item: Optional current item being processed
            sub_operation: Optional sub-operation in progress
            error_count: Number of errors encountered
        """
        if operation not in self.progress_trackers:
            self.progress_trackers[operation] = ProgressInfo(
                operation=operation,
                total_items=total,
                completed_items=0,
                started_at=time.time(),
                status="in_progress"
            )
            
        tracker = self.progress_trackers[operation]
        tracker.completed_items = completed
        tracker.current_item = current_item
        tracker.sub_operation = sub_operation
        tracker.error_count = error_count
        
        # Calculate ETA
        if completed > 0:
            elapsed = time.time() - tracker.started_at
            items_per_sec = completed / elapsed
            remaining_items = total - completed
            tracker.eta = time.time() + (remaining_items / items_per_sec)
            
        # Update status
        if completed >= total:
            tracker.status = "completed"
        elif error_count > 0:
            tracker.status = "error"
            
        # Notify handler if registered
        if operation in self._operation_handlers:
            self._operation_handlers[operation]({
                "completed": completed,
                "total": total,
                "current_item": current_item,
                "sub_operation": sub_operation,
                "error_count": error_count,
                "eta": tracker.eta
            })
            
        # Log progress
        progress_pct = (completed / total) * 100
        logger.info(
            f"{operation}: {progress_pct:.1f}% "
            f"({completed}/{total}) "
            f"[{tracker.status}]"
        )
        
    def get_progress(self, operation: str) -> Optional[ProgressInfo]:
        """Get progress info for an operation."""
        return self.progress_trackers.get(operation)
        
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get current value of a metric."""
        return self.current_metrics.get(name)
        
    @contextmanager
    def track_operation_time(
        self,
        operation: str,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Context manager for tracking operation execution time.
        
        Args:
            operation: Name of the operation to track
            labels: Optional labels for the metric
            
        Example:
            with monitor.track_operation_time("process_pdf", {"file": "doc.pdf"}):
                process_pdf(file)
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_metric(Metric(
                name=f"{operation}_duration_seconds",
                value=duration,
                type=MetricType.HISTOGRAM,
                labels=labels or {}
            ))
            
    def _persist_metric(self, metric: Metric) -> None:
        """
        Persist a metric to disk.
        
        Args:
            metric: The metric to persist
        """
        day_dir = self.metrics_dir / datetime.now().strftime("%Y-%m-%d")
        day_dir.mkdir(exist_ok=True)
        
        metric_file = day_dir / f"{metric.name}.jsonl"
        
        with metric_file.open("a") as f:
            json.dump({
                "name": metric.name,
                "value": metric.value,
                "type": metric.type.value,
                "timestamp": metric.timestamp,
                "labels": metric.labels
            }, f)
            f.write("\n")


# Global monitoring instance
monitor = MonitoringSystem()