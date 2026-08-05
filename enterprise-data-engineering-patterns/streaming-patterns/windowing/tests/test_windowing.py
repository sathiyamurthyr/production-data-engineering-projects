"""Unit tests for the Windowing pattern."""

import pytest

from src.windowing import Windowing, WindowingConfig


class TestWindowingConfig:
    """Tests for WindowingConfig."""

    def test_default_config(self) -> None:
        config = WindowingConfig()
        assert config.pattern_name == "windowing"


class TestWindowing:
    """Tests for Windowing."""

    def test_init_default_config(self) -> None:
        pattern = Windowing()
        assert pattern.config.pattern_name == "windowing"

    def test_init_custom_config(self) -> None:
        config = WindowingConfig()
        pattern = Windowing(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Windowing()
        result = pattern.execute("test_data")
        assert result == "test_data"
