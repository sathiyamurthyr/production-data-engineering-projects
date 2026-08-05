"""Unit tests for the Partition Strategy pattern."""

import pytest

from src.partition_strategy import PartitionStrategy, PartitionStrategyConfig


class TestPartitionStrategyConfig:
    """Tests for PartitionStrategyConfig."""

    def test_default_config(self) -> None:
        config = PartitionStrategyConfig()
        assert config.pattern_name == "partition-strategy"


class TestPartitionStrategy:
    """Tests for PartitionStrategy."""

    def test_init_default_config(self) -> None:
        pattern = PartitionStrategy()
        assert pattern.config.pattern_name == "partition-strategy"

    def test_init_custom_config(self) -> None:
        config = PartitionStrategyConfig()
        pattern = PartitionStrategy(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = PartitionStrategy()
        result = pattern.execute("test_data")
        assert result == "test_data"
