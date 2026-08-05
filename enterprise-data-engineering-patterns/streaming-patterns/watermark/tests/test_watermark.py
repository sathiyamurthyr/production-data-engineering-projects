"""Unit tests for the Watermark pattern."""

import pytest

from src.watermark import Watermark, WatermarkConfig


class TestWatermarkConfig:
    """Tests for WatermarkConfig."""

    def test_default_config(self) -> None:
        config = WatermarkConfig()
        assert config.pattern_name == "watermark"


class TestWatermark:
    """Tests for Watermark."""

    def test_init_default_config(self) -> None:
        pattern = Watermark()
        assert pattern.config.pattern_name == "watermark"

    def test_init_custom_config(self) -> None:
        config = WatermarkConfig()
        pattern = Watermark(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Watermark()
        result = pattern.execute("test_data")
        assert result == "test_data"
