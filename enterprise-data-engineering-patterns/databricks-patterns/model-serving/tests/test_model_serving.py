"""Unit tests for the Model Serving pattern."""

import pytest

from src.model_serving import ModelServing, ModelServingConfig


class TestModelServingConfig:
    """Tests for ModelServingConfig."""

    def test_default_config(self) -> None:
        config = ModelServingConfig()
        assert config.pattern_name == "model-serving"


class TestModelServing:
    """Tests for ModelServing."""

    def test_init_default_config(self) -> None:
        pattern = ModelServing()
        assert pattern.config.pattern_name == "model-serving"

    def test_init_custom_config(self) -> None:
        config = ModelServingConfig()
        pattern = ModelServing(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ModelServing()
        result = pattern.execute("test_data")
        assert result == "test_data"
