"""Unit tests for the Backpressure pattern."""

import pytest

from src.backpressure import Backpressure, BackpressureConfig


class TestBackpressureConfig:
    """Tests for BackpressureConfig."""

    def test_default_config(self) -> None:
        config = BackpressureConfig()
        assert config.pattern_name == "backpressure"


class TestBackpressure:
    """Tests for Backpressure."""

    def test_init_default_config(self) -> None:
        pattern = Backpressure()
        assert pattern.config.pattern_name == "backpressure"

    def test_init_custom_config(self) -> None:
        config = BackpressureConfig()
        pattern = Backpressure(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Backpressure()
        result = pattern.execute("test_data")
        assert result == "test_data"
