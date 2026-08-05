"""Unit tests for the Lambda Architecture pattern."""

import pytest

from src.lambda_architecture import LambdaArchitecture, LambdaArchitectureConfig


class TestLambdaArchitectureConfig:
    """Tests for LambdaArchitectureConfig."""

    def test_default_config(self) -> None:
        config = LambdaArchitectureConfig()
        assert config.pattern_name == "lambda-architecture"


class TestLambdaArchitecture:
    """Tests for LambdaArchitecture."""

    def test_init_default_config(self) -> None:
        pattern = LambdaArchitecture()
        assert pattern.config.pattern_name == "lambda-architecture"

    def test_init_custom_config(self) -> None:
        config = LambdaArchitectureConfig()
        pattern = LambdaArchitecture(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = LambdaArchitecture()
        result = pattern.execute("test_data")
        assert result == "test_data"
