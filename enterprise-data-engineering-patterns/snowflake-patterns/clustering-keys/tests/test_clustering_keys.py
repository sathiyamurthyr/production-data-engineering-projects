"""Unit tests for the Clustering Keys pattern."""

import pytest

from src.clustering_keys import ClusteringKeys, ClusteringKeysConfig


class TestClusteringKeysConfig:
    """Tests for ClusteringKeysConfig."""

    def test_default_config(self) -> None:
        config = ClusteringKeysConfig()
        assert config.pattern_name == "clustering-keys"


class TestClusteringKeys:
    """Tests for ClusteringKeys."""

    def test_init_default_config(self) -> None:
        pattern = ClusteringKeys()
        assert pattern.config.pattern_name == "clustering-keys"

    def test_init_custom_config(self) -> None:
        config = ClusteringKeysConfig()
        pattern = ClusteringKeys(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ClusteringKeys()
        result = pattern.execute("test_data")
        assert result == "test_data"
