"""Unit tests for the Resource Right Sizing pattern."""

import pytest

from src.resource_right_sizing import ResourceRightSizing, ResourceRightSizingConfig


class TestResourceRightSizingConfig:
    """Tests for ResourceRightSizingConfig."""

    def test_default_config(self) -> None:
        config = ResourceRightSizingConfig()
        assert config.pattern_name == "resource-right-sizing"


class TestResourceRightSizing:
    """Tests for ResourceRightSizing."""

    def test_init_default_config(self) -> None:
        pattern = ResourceRightSizing()
        assert pattern.config.pattern_name == "resource-right-sizing"

    def test_init_custom_config(self) -> None:
        config = ResourceRightSizingConfig()
        pattern = ResourceRightSizing(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ResourceRightSizing()
        result = pattern.execute("test_data")
        assert result == "test_data"
