"""Unit tests for the Pools pattern."""

import pytest

from src.pools import Pools, PoolsConfig


class TestPoolsConfig:
    """Tests for PoolsConfig."""

    def test_default_config(self) -> None:
        config = PoolsConfig()
        assert config.pattern_name == "pools"


class TestPools:
    """Tests for Pools."""

    def test_init_default_config(self) -> None:
        pattern = Pools()
        assert pattern.config.pattern_name == "pools"

    def test_init_custom_config(self) -> None:
        config = PoolsConfig()
        pattern = Pools(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Pools()
        result = pattern.execute("test_data")
        assert result == "test_data"
