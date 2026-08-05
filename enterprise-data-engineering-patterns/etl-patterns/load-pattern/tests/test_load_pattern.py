"""Unit tests for the Load Pattern pattern."""

import pytest

from src.load_pattern import LoadPattern, LoadPatternConfig


class TestLoadPatternConfig:
    """Tests for LoadPatternConfig."""

    def test_default_config(self) -> None:
        config = LoadPatternConfig()
        assert config.pattern_name == "load-pattern"


class TestLoadPattern:
    """Tests for LoadPattern."""

    def test_init_default_config(self) -> None:
        pattern = LoadPattern()
        assert pattern.config.pattern_name == "load-pattern"

    def test_init_custom_config(self) -> None:
        config = LoadPatternConfig()
        pattern = LoadPattern(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = LoadPattern()
        result = pattern.execute("test_data")
        assert result == "test_data"
