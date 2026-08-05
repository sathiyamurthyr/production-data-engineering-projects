"""Unit tests for the Transformation Pattern pattern."""

import pytest

from src.transformation_pattern import TransformationPattern, TransformationPatternConfig


class TestTransformationPatternConfig:
    """Tests for TransformationPatternConfig."""

    def test_default_config(self) -> None:
        config = TransformationPatternConfig()
        assert config.pattern_name == "transformation-pattern"


class TestTransformationPattern:
    """Tests for TransformationPattern."""

    def test_init_default_config(self) -> None:
        pattern = TransformationPattern()
        assert pattern.config.pattern_name == "transformation-pattern"

    def test_init_custom_config(self) -> None:
        config = TransformationPatternConfig()
        pattern = TransformationPattern(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = TransformationPattern()
        result = pattern.execute("test_data")
        assert result == "test_data"
