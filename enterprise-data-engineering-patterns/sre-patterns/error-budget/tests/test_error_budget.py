"""Unit tests for the Error Budget pattern."""

import pytest

from src.error_budget import ErrorBudget, ErrorBudgetConfig


class TestErrorBudgetConfig:
    """Tests for ErrorBudgetConfig."""

    def test_default_config(self) -> None:
        config = ErrorBudgetConfig()
        assert config.pattern_name == "error-budget"


class TestErrorBudget:
    """Tests for ErrorBudget."""

    def test_init_default_config(self) -> None:
        pattern = ErrorBudget()
        assert pattern.config.pattern_name == "error-budget"

    def test_init_custom_config(self) -> None:
        config = ErrorBudgetConfig()
        pattern = ErrorBudget(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ErrorBudget()
        result = pattern.execute("test_data")
        assert result == "test_data"
