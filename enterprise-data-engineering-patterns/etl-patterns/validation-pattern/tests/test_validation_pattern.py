"""Unit tests for the Validation Pattern pattern."""

import pytest

from src.validation_pattern import ValidationPattern, ValidationPatternConfig


class TestValidationPatternConfig:
    """Tests for ValidationPatternConfig."""

    def test_default_config(self) -> None:
        config = ValidationPatternConfig()
        assert config.pattern_name == "validation-pattern"


class TestValidationPattern:
    """Tests for ValidationPattern."""

    def test_init_default_config(self) -> None:
        pattern = ValidationPattern()
        assert pattern.config.pattern_name == "validation-pattern"

    def test_init_custom_config(self) -> None:
        config = ValidationPatternConfig()
        pattern = ValidationPattern(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ValidationPattern()
        result = pattern.execute("test_data")
        assert result == "test_data"
