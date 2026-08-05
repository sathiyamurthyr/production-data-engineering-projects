"""Unit tests for the Data Masking pattern."""

import pytest

from src.data_masking import DataMasking, DataMaskingConfig


class TestDataMaskingConfig:
    """Tests for DataMaskingConfig."""

    def test_default_config(self) -> None:
        config = DataMaskingConfig()
        assert config.pattern_name == "data-masking"


class TestDataMasking:
    """Tests for DataMasking."""

    def test_init_default_config(self) -> None:
        pattern = DataMasking()
        assert pattern.config.pattern_name == "data-masking"

    def test_init_custom_config(self) -> None:
        config = DataMaskingConfig()
        pattern = DataMasking(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataMasking()
        result = pattern.execute("test_data")
        assert result == "test_data"
