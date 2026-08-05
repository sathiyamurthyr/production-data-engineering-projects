"""Unit tests for the Timestamp-based CDC pattern."""

import pytest

from src.timestamp_based_cdc import TimestampBasedCdc, TimestampBasedCdcConfig


class TestTimestampBasedCdcConfig:
    """Tests for TimestampBasedCdcConfig."""

    def test_default_config(self) -> None:
        config = TimestampBasedCdcConfig()
        assert config.pattern_name == "timestamp-based-cdc"


class TestTimestampBasedCdc:
    """Tests for TimestampBasedCdc."""

    def test_init_default_config(self) -> None:
        pattern = TimestampBasedCdc()
        assert pattern.config.pattern_name == "timestamp-based-cdc"

    def test_init_custom_config(self) -> None:
        config = TimestampBasedCdcConfig()
        pattern = TimestampBasedCdc(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = TimestampBasedCdc()
        result = pattern.execute("test_data")
        assert result == "test_data"
