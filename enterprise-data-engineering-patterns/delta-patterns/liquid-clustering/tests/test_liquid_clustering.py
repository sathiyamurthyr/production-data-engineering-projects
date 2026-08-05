"""Unit tests for the Liquid Clustering Concepts pattern."""

import pytest

from src.liquid_clustering import LiquidClustering, LiquidClusteringConfig


class TestLiquidClusteringConfig:
    """Tests for LiquidClusteringConfig."""

    def test_default_config(self) -> None:
        config = LiquidClusteringConfig()
        assert config.pattern_name == "liquid-clustering"


class TestLiquidClustering:
    """Tests for LiquidClustering."""

    def test_init_default_config(self) -> None:
        pattern = LiquidClustering()
        assert pattern.config.pattern_name == "liquid-clustering"

    def test_init_custom_config(self) -> None:
        config = LiquidClusteringConfig()
        pattern = LiquidClustering(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = LiquidClustering()
        result = pattern.execute("test_data")
        assert result == "test_data"
