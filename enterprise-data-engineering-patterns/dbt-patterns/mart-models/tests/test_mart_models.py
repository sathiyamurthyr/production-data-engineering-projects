"""Unit tests for the Mart Models pattern."""

import pytest

from src.mart_models import MartModels, MartModelsConfig


class TestMartModelsConfig:
    """Tests for MartModelsConfig."""

    def test_default_config(self) -> None:
        config = MartModelsConfig()
        assert config.pattern_name == "mart-models"


class TestMartModels:
    """Tests for MartModels."""

    def test_init_default_config(self) -> None:
        pattern = MartModels()
        assert pattern.config.pattern_name == "mart-models"

    def test_init_custom_config(self) -> None:
        config = MartModelsConfig()
        pattern = MartModels(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = MartModels()
        result = pattern.execute("test_data")
        assert result == "test_data"
