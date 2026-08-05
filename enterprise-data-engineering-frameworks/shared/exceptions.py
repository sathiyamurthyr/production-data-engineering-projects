"""Common exceptions used across all frameworks."""
from __future__ import annotations


class FrameworkError(Exception):
    """Base exception for all framework errors."""
    def __init__(self, message: str, code: str | None = None, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code or "FRAMEWORK_ERROR"
        self.details = details or {}


class ConfigurationError(FrameworkError):
    """Raised when configuration is invalid."""


class ValidationError(FrameworkError):
    """Raised when data validation fails."""


class ConnectionError(FrameworkError):
    """Raised when a connection cannot be established."""


class RetryExhaustedError(FrameworkError):
    """Raised when retry attempts are exhausted."""


class PluginError(FrameworkError):
    """Raised when a plugin fails to load or execute."""


class PipelineError(FrameworkError):
    """Raised when a pipeline execution fails."""


class QualityError(FrameworkError):
    """Raised when data quality checks fail."""


class SecretError(FrameworkError):
    """Raised when secret retrieval fails."""

