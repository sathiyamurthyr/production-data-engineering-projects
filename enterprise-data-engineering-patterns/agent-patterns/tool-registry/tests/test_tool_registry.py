"""Unit tests for the Tool Registry pattern."""

import pytest

from src.tool_registry import ToolRegistry, ToolRegistryConfig


class TestToolRegistryConfig:
    """Tests for ToolRegistryConfig."""

    def test_default_config(self) -> None:
        config = ToolRegistryConfig()
        assert config.pattern_name == "tool-registry"


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_init_default_config(self) -> None:
        pattern = ToolRegistry()
        assert pattern.config.pattern_name == "tool-registry"

    def test_init_custom_config(self) -> None:
        config = ToolRegistryConfig()
        pattern = ToolRegistry(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ToolRegistry()
        result = pattern.execute("test_data")
        assert result == "test_data"
