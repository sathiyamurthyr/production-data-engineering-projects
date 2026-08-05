"""Unit tests for the Data Discovery pattern."""

import pytest

from src.data_discovery import DataDiscovery, DataDiscoveryConfig


class TestDataDiscoveryConfig:
    """Tests for DataDiscoveryConfig."""

    def test_default_config(self) -> None:
        config = DataDiscoveryConfig()
        assert config.pattern_name == "data-discovery"


class TestDataDiscovery:
    """Tests for DataDiscovery."""

    def test_init_default_config(self) -> None:
        pattern = DataDiscovery()
        assert pattern.config.pattern_name == "data-discovery"

    def test_init_custom_config(self) -> None:
        config = DataDiscoveryConfig()
        pattern = DataDiscovery(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataDiscovery()
        result = pattern.execute("test_data")
        assert result == "test_data"
