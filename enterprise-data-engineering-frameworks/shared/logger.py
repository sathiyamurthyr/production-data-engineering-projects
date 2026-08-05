"""Structured logging setup for all frameworks."""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(level: str = "INFO", json_output: bool = False, log_file: str | None = None) -> structlog.BoundLogger:
    """Configure structured logging."""
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=getattr(logging, level.upper(), logging.INFO))
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    structlog.configure(processors=processors, logger_factory=structlog.PrintLoggerFactory(), cache_logger_on_first_use=True)
    if log_file:
        handler = logging.FileHandler(log_file)
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        logging.getLogger().addHandler(handler)
    return structlog.get_logger()

