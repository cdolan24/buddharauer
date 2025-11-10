"""Unit tests for logging setup."""
import os
import logging
from src.utils.logging import get_logger

def test_get_logger_creates_new_logger():
    """Test creating a new logger."""
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    assert len(logger.handlers) > 0

def test_get_logger_reuses_existing_logger():
    """Test logger reuse with same name."""
    logger1 = get_logger("reuse_test")
    logger2 = get_logger("reuse_test")
    assert logger1 is logger2
    # Should not create duplicate handlers
    assert len(logger1.handlers) == len(logger2.handlers)

def test_get_logger_handlers():
    """Test logger has correct handlers setup."""
    logger = get_logger("handler_test")
    handler_types = [type(h) for h in logger.handlers]
    assert logging.FileHandler in handler_types
    assert logging.StreamHandler in handler_types

def test_get_logger_level():
    """Test logger respects configured level."""
    logger = get_logger("level_test")
    assert logger.level == getattr(logging, os.getenv("LOG_LEVEL", "INFO"))