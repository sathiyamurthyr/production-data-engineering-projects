"""Unit tests for the Incremental Models pattern."""

import pytest

from src.incremental_models import IncrementalModels, IncrementalModelsConfig


class TestIncrementalModelsConfig:
    """Tests for IncrementalModelsConfig."""

    def test_default_config(self) -> None:
        config = IncrementalModelsConfig()
        assert config.pattern_name == "incremental-models"


class TestIncrementalModels:
    """Tests for IncrementalModels."""

    def test_init_default_config(self) -> None:
        pattern = IncrementalModels()
        assert pattern.config.pattern_name == "incremental-models"

    def test_init_custom_config(self) -> None:
        config = IncrementalModelsConfig()
        pattern = IncrementalModels(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = IncrementalModels()
        result = pattern.execute("test_data")
        assert result == "test_data"
