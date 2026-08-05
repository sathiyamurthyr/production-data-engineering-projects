"""Unit tests for the Silver Layer pattern."""

import pytest

from src.silver_layer import SilverLayer, SilverLayerConfig


class TestSilverLayerConfig:
    """Tests for SilverLayerConfig."""

    def test_default_config(self) -> None:
        config = SilverLayerConfig()
        assert config.pattern_name == "silver-layer"


class TestSilverLayer:
    """Tests for SilverLayer."""

    def test_init_default_config(self) -> None:
        pattern = SilverLayer()
        assert pattern.config.pattern_name == "silver-layer"

    def test_init_custom_config(self) -> None:
        config = SilverLayerConfig()
        pattern = SilverLayer(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = SilverLayer()
        result = pattern.execute("test_data")
        assert result == "test_data"
