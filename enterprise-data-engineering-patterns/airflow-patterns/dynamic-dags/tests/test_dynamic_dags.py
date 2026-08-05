"""Unit tests for the Dynamic DAGs pattern."""

import pytest

from src.dynamic_dags import DynamicDags, DynamicDagsConfig


class TestDynamicDagsConfig:
    """Tests for DynamicDagsConfig."""

    def test_default_config(self) -> None:
        config = DynamicDagsConfig()
        assert config.pattern_name == "dynamic-dags"


class TestDynamicDags:
    """Tests for DynamicDags."""

    def test_init_default_config(self) -> None:
        pattern = DynamicDags()
        assert pattern.config.pattern_name == "dynamic-dags"

    def test_init_custom_config(self) -> None:
        config = DynamicDagsConfig()
        pattern = DynamicDags(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DynamicDags()
        result = pattern.execute("test_data")
        assert result == "test_data"
