"""Unit tests for the Log-based CDC pattern."""

import pytest

from src.log_based_cdc import LogBasedCdc, LogBasedCdcConfig


class TestLogBasedCdcConfig:
    """Tests for LogBasedCdcConfig."""

    def test_default_config(self) -> None:
        config = LogBasedCdcConfig()
        assert config.pattern_name == "log-based-cdc"


class TestLogBasedCdc:
    """Tests for LogBasedCdc."""

    def test_init_default_config(self) -> None:
        pattern = LogBasedCdc()
        assert pattern.config.pattern_name == "log-based-cdc"

    def test_init_custom_config(self) -> None:
        config = LogBasedCdcConfig()
        pattern = LogBasedCdc(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = LogBasedCdc()
        result = pattern.execute("test_data")
        assert result == "test_data"
