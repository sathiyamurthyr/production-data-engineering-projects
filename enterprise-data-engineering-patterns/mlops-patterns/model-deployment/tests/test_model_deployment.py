"""Unit tests for the Model Deployment pattern."""

import pytest

from src.model_deployment import ModelDeployment, ModelDeploymentConfig


class TestModelDeploymentConfig:
    """Tests for ModelDeploymentConfig."""

    def test_default_config(self) -> None:
        config = ModelDeploymentConfig()
        assert config.pattern_name == "model-deployment"


class TestModelDeployment:
    """Tests for ModelDeployment."""

    def test_init_default_config(self) -> None:
        pattern = ModelDeployment()
        assert pattern.config.pattern_name == "model-deployment"

    def test_init_custom_config(self) -> None:
        config = ModelDeploymentConfig()
        pattern = ModelDeployment(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ModelDeployment()
        result = pattern.execute("test_data")
        assert result == "test_data"
