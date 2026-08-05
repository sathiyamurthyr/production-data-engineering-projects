"""Unit tests for the Model Registry pattern."""

import pytest

from src.model_registry import ModelRegistry, ModelRegistryConfig


class TestModelRegistryConfig:
    """Tests for ModelRegistryConfig."""

    def test_default_config(self) -> None:
        config = ModelRegistryConfig()
        assert config.pattern_name == "model-registry"


class TestModelRegistry:
    """Tests for ModelRegistry."""

    def test_init_default_config(self) -> None:
        pattern = ModelRegistry()
        assert pattern.config.pattern_name == "model-registry"

    def test_init_custom_config(self) -> None:
        config = ModelRegistryConfig()
        pattern = ModelRegistry(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ModelRegistry()
        result = pattern.execute("test_data")
        assert result == "test_data"
