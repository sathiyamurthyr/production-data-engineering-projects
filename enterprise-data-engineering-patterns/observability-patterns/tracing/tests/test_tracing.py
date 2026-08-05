"""Unit tests for the Tracing Concepts pattern."""

import pytest

from src.tracing import Tracing, TracingConfig


class TestTracingConfig:
    """Tests for TracingConfig."""

    def test_default_config(self) -> None:
        config = TracingConfig()
        assert config.pattern_name == "tracing"


class TestTracing:
    """Tests for Tracing."""

    def test_init_default_config(self) -> None:
        pattern = Tracing()
        assert pattern.config.pattern_name == "tracing"

    def test_init_custom_config(self) -> None:
        config = TracingConfig()
        pattern = Tracing(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Tracing()
        result = pattern.execute("test_data")
        assert result == "test_data"
