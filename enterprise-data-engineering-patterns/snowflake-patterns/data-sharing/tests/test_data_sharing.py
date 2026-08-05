"""Unit tests for the Data Sharing pattern."""

import pytest

from src.data_sharing import DataSharing, DataSharingConfig


class TestDataSharingConfig:
    """Tests for DataSharingConfig."""

    def test_default_config(self) -> None:
        config = DataSharingConfig()
        assert config.pattern_name == "data-sharing"


class TestDataSharing:
    """Tests for DataSharing."""

    def test_init_default_config(self) -> None:
        pattern = DataSharing()
        assert pattern.config.pattern_name == "data-sharing"

    def test_init_custom_config(self) -> None:
        config = DataSharingConfig()
        pattern = DataSharing(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataSharing()
        result = pattern.execute("test_data")
        assert result == "test_data"
