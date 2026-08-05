"""Unit tests for the Exactly Once Concepts pattern."""

import pytest

from src.exactly_once import ExactlyOnce, ExactlyOnceConfig


class TestExactlyOnceConfig:
    """Tests for ExactlyOnceConfig."""

    def test_default_config(self) -> None:
        config = ExactlyOnceConfig()
        assert config.pattern_name == "exactly-once"


class TestExactlyOnce:
    """Tests for ExactlyOnce."""

    def test_init_default_config(self) -> None:
        pattern = ExactlyOnce()
        assert pattern.config.pattern_name == "exactly-once"

    def test_init_custom_config(self) -> None:
        config = ExactlyOnceConfig()
        pattern = ExactlyOnce(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ExactlyOnce()
        result = pattern.execute("test_data")
        assert result == "test_data"
