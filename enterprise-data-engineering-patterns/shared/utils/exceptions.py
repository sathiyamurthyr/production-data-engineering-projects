"""Custom exception classes for enterprise data engineering patterns.

All patterns should use these exception types for consistent error handling
across the repository.
"""

from __future__ import annotations


class PatternError(Exception):
    """Base exception for all pattern-related errors."""

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


class ValidationError(PatternError):
    """Raised when input validation fails."""


class ConfigurationError(PatternError):
    """Raised when configuration is invalid or missing."""


class DataQualityError(PatternError):
    """Raised when data quality checks fail."""

    def __init__(
        self,
        message: str,
        quality_score: float | None = None,
        failed_checks: list[str] | None = None,
        **context: object,
    ) -> None:
        super().__init__(message, **context)
        self.quality_score = quality_score
        self.failed_checks = failed_checks or []


class PipelineError(PatternError):
    """Raised when a data pipeline execution fails."""

    def __init__(
        self,
        message: str,
        stage: str | None = None,
        cause: Exception | None = None,
        **context: object,
    ) -> None:
        super().__init__(message, **context)
        self.stage = stage
        self.__cause__ = cause
