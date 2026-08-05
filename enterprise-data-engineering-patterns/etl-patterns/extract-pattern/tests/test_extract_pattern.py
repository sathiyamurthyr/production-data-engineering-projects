"""Unit tests for the Extract Pattern pattern."""

import pytest

from src.extract_pattern import ExtractPattern, ExtractPatternConfig


class TestExtractPatternConfig:
    """Tests for ExtractPatternConfig."""

    def test_default_config(self) -> None:
        config = ExtractPatternConfig()
        assert config.pattern_name == "extract-pattern"


class TestExtractPattern:
    """Tests for ExtractPattern."""

    def test_init_default_config(self) -> None:
        pattern = ExtractPattern()
        assert pattern.config.pattern_name == "extract-pattern"

    def test_init_custom_config(self) -> None:
        config = ExtractPatternConfig()
        pattern = ExtractPattern(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ExtractPattern()
        result = pattern.execute("test_data")
        assert result == "test_data"
