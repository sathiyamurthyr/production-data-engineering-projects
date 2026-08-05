"""Unit tests for the Gold Layer pattern."""

import pytest

from src.gold_layer import GoldLayer, GoldLayerConfig


class TestGoldLayerConfig:
    """Tests for GoldLayerConfig."""

    def test_default_config(self) -> None:
        config = GoldLayerConfig()
        assert config.pattern_name == "gold-layer"


class TestGoldLayer:
    """Tests for GoldLayer."""

    def test_init_default_config(self) -> None:
        pattern = GoldLayer()
        assert pattern.config.pattern_name == "gold-layer"

    def test_init_custom_config(self) -> None:
        config = GoldLayerConfig()
        pattern = GoldLayer(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = GoldLayer()
        result = pattern.execute("test_data")
        assert result == "test_data"
