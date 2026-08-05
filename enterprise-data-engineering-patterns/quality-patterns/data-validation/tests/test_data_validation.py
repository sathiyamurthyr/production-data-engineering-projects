"""Unit tests for the Data Validation pattern."""

import pytest

from src.data_validation import DataValidation, DataValidationConfig


class TestDataValidationConfig:
    """Tests for DataValidationConfig."""

    def test_default_config(self) -> None:
        config = DataValidationConfig()
        assert config.pattern_name == "data-validation"


class TestDataValidation:
    """Tests for DataValidation."""

    def test_init_default_config(self) -> None:
        pattern = DataValidation()
        assert pattern.config.pattern_name == "data-validation"

    def test_init_custom_config(self) -> None:
        config = DataValidationConfig()
        pattern = DataValidation(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataValidation()
        result = pattern.execute("test_data")
        assert result == "test_data"
