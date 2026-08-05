"""Unit tests for the Bronze Layer pattern."""

import pytest

from src.bronze_layer import BronzeLayer, BronzeLayerConfig


class TestBronzeLayerConfig:
    """Tests for BronzeLayerConfig."""

    def test_default_config(self) -> None:
        config = BronzeLayerConfig()
        assert config.pattern_name == "bronze-layer"


class TestBronzeLayer:
    """Tests for BronzeLayer."""

    def test_init_default_config(self) -> None:
        pattern = BronzeLayer()
        assert pattern.config.pattern_name == "bronze-layer"

    def test_init_custom_config(self) -> None:
        config = BronzeLayerConfig()
        pattern = BronzeLayer(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = BronzeLayer()
        result = pattern.execute("test_data")
        assert result == "test_data"
