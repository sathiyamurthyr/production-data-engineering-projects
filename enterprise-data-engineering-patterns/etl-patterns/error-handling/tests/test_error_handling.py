"""Unit tests for the Error Handling pattern."""

import pytest

from src.error_handling import ErrorHandling, ErrorHandlingConfig


class TestErrorHandlingConfig:
    """Tests for ErrorHandlingConfig."""

    def test_default_config(self) -> None:
        config = ErrorHandlingConfig()
        assert config.pattern_name == "error-handling"


class TestErrorHandling:
    """Tests for ErrorHandling."""

    def test_init_default_config(self) -> None:
        pattern = ErrorHandling()
        assert pattern.config.pattern_name == "error-handling"

    def test_init_custom_config(self) -> None:
        config = ErrorHandlingConfig()
        pattern = ErrorHandling(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ErrorHandling()
        result = pattern.execute("test_data")
        assert result == "test_data"
