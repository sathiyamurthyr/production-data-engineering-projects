"""Unit tests for the Late Data Handling pattern."""

import pytest

from src.late_data_handling import LateDataHandling, LateDataHandlingConfig


class TestLateDataHandlingConfig:
    """Tests for LateDataHandlingConfig."""

    def test_default_config(self) -> None:
        config = LateDataHandlingConfig()
        assert config.pattern_name == "late-data-handling"


class TestLateDataHandling:
    """Tests for LateDataHandling."""

    def test_init_default_config(self) -> None:
        pattern = LateDataHandling()
        assert pattern.config.pattern_name == "late-data-handling"

    def test_init_custom_config(self) -> None:
        config = LateDataHandlingConfig()
        pattern = LateDataHandling(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = LateDataHandling()
        result = pattern.execute("test_data")
        assert result == "test_data"
