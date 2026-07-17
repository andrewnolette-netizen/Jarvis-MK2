"""
Logging configuration for JARVIS-MK2.
Sets up logging based on configuration.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

_is_setup = False


def setup_logging() -> None:
    """
    Set up logging for the application.
    Configures the root logger.
    """
    global _is_setup
    if _is_setup:
        return

    # Import config here to avoid circular imports
    from .config import config

    # Get logging configuration
    log_level = config.get("system.log_level", "INFO")
    log_format = config.get(
        "system.log_format",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    log_file = config.get("system.log_file", "logs/jarvis.log")

    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    # Prevent adding handlers multiple times
    if logger.handlers:
        # Already has handlers, we assume they are ours
        return

    # Create formatters
    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file is specified)
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (if None, returns root logger)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(name)
    else:
        return logging.getLogger()


# Initialize logging when module is imported
# We delay this until logging is actually needed to avoid circular import issues
# setup_logging()  # Commented out to prevent circular import during initialization