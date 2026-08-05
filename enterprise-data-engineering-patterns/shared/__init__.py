"""Shared utilities for Enterprise Data Engineering Patterns.

This package provides reusable components across all patterns:
- Structured logging configuration
- Configuration management
- Error handling utilities
- Metrics collection
- Testing utilities
"""

from shared.logger import get_logger, configure_logging
from shared.config import PatternConfig, load_config

__all__ = [
    "get_logger",
    "configure_logging",
    "PatternConfig",
    "load_config",
]