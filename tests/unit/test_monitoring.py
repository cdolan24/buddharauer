"""Tests for monitoring functionality."""
import asyncio
from pathlib import Path
import pytest
import time
from unittest.mock import Mock, patch
import json

from src.pipeline.monitoring import (
    MonitoringSystem,
    Metric,
    MetricType,
    ProgressInfo,
    monitor
)


@pytest.fixture
def monitoring_system(tmp_path):
    """Create a monitoring system instance."""
    return MonitoringSystem(tmp_path / "metrics")


def test_metric_recording(monitoring_system):
    """Test recording and retrieving metrics."""
    metric = Metric(
        name="test_metric",
        value=42.0,
        type=MetricType.COUNTER,
        labels={"test": "value"}
    )
    
    monitoring_system.record_metric(metric)
    
    retrieved = monitoring_system.get_metric("test_metric")
    assert retrieved is not None
    assert retrieved.value == 42.0
    assert retrieved.type == MetricType.COUNTER
    assert retrieved.labels == {"test": "value"}


def test_progress_tracking(monitoring_system):
    """Test operation progress tracking."""
    monitoring_system.update_progress(
        operation="test_op",
        completed=5,
        total=10,
        current_item="item_5",
        sub_operation="processing",
        error_count=1
    )
    
    progress = monitoring_system.get_progress("test_op")
    assert progress is not None
    assert progress.completed_items == 5
    assert progress.total_items == 10
    assert progress.current_item == "item_5"
    assert progress.sub_operation == "processing"
    assert progress.error_count == 1
    assert progress.status == "error"  # Due to error_count > 0


def test_operation_handler(monitoring_system):
    """Test operation event handlers."""
    handler_called = False
    handler_data = None
    
    def test_handler(data):
        nonlocal handler_called, handler_data
        handler_called = True
        handler_data = data
    
    monitoring_system.register_operation("test_op", test_handler)
    
    monitoring_system.update_progress(
        operation="test_op",
        completed=1,
        total=2,
        current_item="test"
    )
    
    assert handler_called
    assert handler_data["completed"] == 1
    assert handler_data["total"] == 2
    assert handler_data["current_item"] == "test"


def test_metric_persistence(monitoring_system, tmp_path):
    """Test metric persistence to disk."""
    metric = Metric(
        name="test_metric",
        value=42.0,
        type=MetricType.COUNTER,
        timestamp=123456.0,
        labels={"test": "value"}
    )
    
    monitoring_system.record_metric(metric)
    
    # Check that metric was written to disk
    metric_files = list(tmp_path.glob("**/test_metric.jsonl"))
    assert len(metric_files) == 1
    
    # Verify content
    with metric_files[0].open() as f:
        data = json.loads(f.read())
        assert data["name"] == "test_metric"
        assert data["value"] == 42.0
        assert data["type"] == "counter"
        assert data["timestamp"] == 123456.0
        assert data["labels"] == {"test": "value"}


@pytest.mark.asyncio
async def test_operation_timing(monitoring_system):
    """Test operation timing context manager."""
    async def test_operation():
        await asyncio.sleep(0.1)
    
    with monitoring_system.track_operation_time(
        "test_operation",
        labels={"type": "test"}
    ):
        await test_operation()
    
    metric = monitoring_system.get_metric("test_operation_duration_seconds")
    assert metric is not None
    assert metric.value >= 0.1
    assert metric.type == MetricType.HISTOGRAM
    assert metric.labels == {"type": "test"}


def test_progress_eta_calculation(monitoring_system):
    """Test ETA calculation in progress tracking."""
    # Simulate start of operation - start tracker at time t=0
    start_time = time.time()

    # First update at start_time to create the tracker
    with patch('time.time', return_value=start_time):
        monitoring_system.update_progress(
            operation="test_op",
            completed=0,
            total=20
        )

    # Second update after 1 second (simulated) with 5 items completed
    with patch('time.time', return_value=start_time + 1.0):
        monitoring_system.update_progress(
            operation="test_op",
            completed=5,
            total=20
        )

        progress = monitoring_system.get_progress("test_op")
        assert progress.eta is not None
        # With 5 items in 1 second, remaining 15 should take 3 seconds
        expected_eta = start_time + 4.0  # 1 second elapsed + 3 seconds remaining
        assert abs(progress.eta - expected_eta) < 0.1


def test_global_monitor_instance():
    """Test the global monitor instance."""
    assert monitor is not None
    
    metric = Metric(
        name="global_test",
        value=1.0,
        type=MetricType.COUNTER
    )
    
    monitor.record_metric(metric)
    assert monitor.get_metric("global_test") is not None