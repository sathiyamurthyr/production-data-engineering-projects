"""Unit tests for the Retry Logic pattern."""

import pytest

from src.retry_logic import RetryLogic, RetryLogicConfig


class TestRetryLogicConfig:
    """Tests for RetryLogicConfig."""

    def test_default_config(self) -> None:
        config = RetryLogicConfig()
        assert config.pattern_name == "retry-logic"


class TestRetryLogic:
    """Tests for RetryLogic."""

    def test_init_default_config(self) -> None:
        pattern = RetryLogic()
        assert pattern.config.pattern_name == "retry-logic"

    def test_init_custom_config(self) -> None:
        config = RetryLogicConfig()
        pattern = RetryLogic(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = RetryLogic()
        result = pattern.execute("test_data")
        assert result == "test_data"
