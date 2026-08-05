"""Unit tests for the Window Trigger pattern."""

import pytest

from src.window_trigger import WindowTrigger, WindowTriggerConfig


class TestWindowTriggerConfig:
    """Tests for WindowTriggerConfig."""

    def test_default_config(self) -> None:
        config = WindowTriggerConfig()
        assert config.pattern_name == "window-trigger"


class TestWindowTrigger:
    """Tests for WindowTrigger."""

    def test_init_default_config(self) -> None:
        pattern = WindowTrigger()
        assert pattern.config.pattern_name == "window-trigger"

    def test_init_custom_config(self) -> None:
        config = WindowTriggerConfig()
        pattern = WindowTrigger(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = WindowTrigger()
        result = pattern.execute("test_data")
        assert result == "test_data"
