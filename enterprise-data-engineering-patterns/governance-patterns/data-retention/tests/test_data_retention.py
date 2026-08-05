"""Unit tests for the Data Retention pattern."""

import pytest

from src.data_retention import DataRetention, DataRetentionConfig


class TestDataRetentionConfig:
    """Tests for DataRetentionConfig."""

    def test_default_config(self) -> None:
        config = DataRetentionConfig()
        assert config.pattern_name == "data-retention"


class TestDataRetention:
    """Tests for DataRetention."""

    def test_init_default_config(self) -> None:
        pattern = DataRetention()
        assert pattern.config.pattern_name == "data-retention"

    def test_init_custom_config(self) -> None:
        config = DataRetentionConfig()
        pattern = DataRetention(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataRetention()
        result = pattern.execute("test_data")
        assert result == "test_data"
