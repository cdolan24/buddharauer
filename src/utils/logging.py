"""Logging setup for Buddharauer.

Configures logging format, level, and file output.
"""
import logging
import os
from typing import Optional

LOG_FILE = os.getenv("LOG_FILE", "buddharauer.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Create and configure a logger.

    Args:
        name: Optional logger name.
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Reset handlers if any exist
    logger.handlers = []
    
    # Set level from environment or default
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO"))
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # Add file handler
    fh = logging.FileHandler(LOG_FILE)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # Add stream handler
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    
    return logger

# Example usage
if __name__ == "__main__":
    log = get_logger("buddharauer")
    log.info("Logger initialized.")
