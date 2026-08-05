"""Unit tests for the Golden Path pattern."""

import pytest

from src.golden_path import GoldenPath, GoldenPathConfig


class TestGoldenPathConfig:
    """Tests for GoldenPathConfig."""

    def test_default_config(self) -> None:
        config = GoldenPathConfig()
        assert config.pattern_name == "golden-path"


class TestGoldenPath:
    """Tests for GoldenPath."""

    def test_init_default_config(self) -> None:
        pattern = GoldenPath()
        assert pattern.config.pattern_name == "golden-path"

    def test_init_custom_config(self) -> None:
        config = GoldenPathConfig()
        pattern = GoldenPath(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = GoldenPath()
        result = pattern.execute("test_data")
        assert result == "test_data"
