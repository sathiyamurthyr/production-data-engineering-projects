"""Unit tests for the Data Fabric pattern."""

import pytest

from src.data_fabric import DataFabric, DataFabricConfig


class TestDataFabricConfig:
    """Tests for DataFabricConfig."""

    def test_default_config(self) -> None:
        config = DataFabricConfig()
        assert config.pattern_name == "data-fabric"


class TestDataFabric:
    """Tests for DataFabric."""

    def test_init_default_config(self) -> None:
        pattern = DataFabric()
        assert pattern.config.pattern_name == "data-fabric"

    def test_init_custom_config(self) -> None:
        config = DataFabricConfig()
        pattern = DataFabric(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataFabric()
        result = pattern.execute("test_data")
        assert result == "test_data"
