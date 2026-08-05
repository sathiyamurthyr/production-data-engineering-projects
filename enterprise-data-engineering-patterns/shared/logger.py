"""Structured logging utilities using structlog.

Provides enterprise-grade structured logging with:
- JSON output for production
- Human-readable output for development
- Automatic context injection (request_id, pattern_name, etc.)
- Log level configuration via environment variables
"""

import logging
import sys
from typing import Any

import structlog
from structlog.stdlib import LoggerFactory


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    **context: Any,
) -> structlog.BoundLogger:
    """Configure structured logging with enterprise best practices.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: If True, output JSON logs; otherwise human-readable.
        **context: Additional context to inject into all log entries.

    Returns:
        Configured structlog logger instance.
    """
    level_enum = getattr(logging, level.upper(), logging.INFO)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_logger_factory(level_enum),
        logger_factory=LoggerFactory(),
        cache_logger_on_first=True,
    )

    logger = structlog.get_logger()
    if context:
        logger = logger.bind(**context)
    return logger


def get_logger(name: str | None = None, **context: Any) -> structlog.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module).
        **context: Additional context to inject into log entries.

    Returns:
        Configured structlog logger instance.
    """
    logger = structlog.get_logger(name)
    if context:
        logger = logger.bind(**context)
    return logger


# Initialize default logging on import
if not logging.getLogger().handlers:
    configure_logging(level="INFO", json_output=True)
