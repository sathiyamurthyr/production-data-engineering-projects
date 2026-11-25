"""
Pipeline logger module for structured console and file logging setup.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional, Union

from src.utils.file_utils import ensure_directory


class JSONLogFormatter(logging.Formatter):
    """Structured JSON formatter for production log aggregation systems (ELK, Datadog)."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt or "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logger(
    name: str = "etl_pipeline",
    log_level: str = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    json_format: bool = False
) -> logging.Logger:
    """
    Configure root or pipeline logger with console and optional file appenders.

    Args:
        name: Logger module hierarchy name.
        log_level: Desired log verbosity ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        log_file: Path to log file destination.
        json_format: If True, emits JSON logs; otherwise standard human-readable text.

    Returns:
        logging.Logger: Initialized logger instance.
    """
    logger = logging.getLogger(name)
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if json_format:
        formatter = JSONLogFormatter()
    else:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    if log_file:
        file_path = Path(log_file)
        ensure_directory(file_path)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
