"""Unit tests for the Staging Models pattern."""

import pytest

from src.staging_models import StagingModels, StagingModelsConfig


class TestStagingModelsConfig:
    """Tests for StagingModelsConfig."""

    def test_default_config(self) -> None:
        config = StagingModelsConfig()
        assert config.pattern_name == "staging-models"


class TestStagingModels:
    """Tests for StagingModels."""

    def test_init_default_config(self) -> None:
        pattern = StagingModels()
        assert pattern.config.pattern_name == "staging-models"

    def test_init_custom_config(self) -> None:
        config = StagingModelsConfig()
        pattern = StagingModels(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = StagingModels()
        result = pattern.execute("test_data")
        assert result == "test_data"
