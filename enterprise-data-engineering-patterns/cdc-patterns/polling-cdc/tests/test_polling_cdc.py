"""Unit tests for the Polling CDC pattern."""

import pytest

from src.polling_cdc import PollingCdc, PollingCdcConfig


class TestPollingCdcConfig:
    """Tests for PollingCdcConfig."""

    def test_default_config(self) -> None:
        config = PollingCdcConfig()
        assert config.pattern_name == "polling-cdc"


class TestPollingCdc:
    """Tests for PollingCdc."""

    def test_init_default_config(self) -> None:
        pattern = PollingCdc()
        assert pattern.config.pattern_name == "polling-cdc"

    def test_init_custom_config(self) -> None:
        config = PollingCdcConfig()
        pattern = PollingCdc(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = PollingCdc()
        result = pattern.execute("test_data")
        assert result == "test_data"
