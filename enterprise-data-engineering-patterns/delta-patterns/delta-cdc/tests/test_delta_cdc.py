"""Unit tests for the CDC with Delta pattern."""

import pytest

from src.delta_cdc import DeltaCdc, DeltaCdcConfig


class TestDeltaCdcConfig:
    """Tests for DeltaCdcConfig."""

    def test_default_config(self) -> None:
        config = DeltaCdcConfig()
        assert config.pattern_name == "delta-cdc"


class TestDeltaCdc:
    """Tests for DeltaCdc."""

    def test_init_default_config(self) -> None:
        pattern = DeltaCdc()
        assert pattern.config.pattern_name == "delta-cdc"

    def test_init_custom_config(self) -> None:
        config = DeltaCdcConfig()
        pattern = DeltaCdc(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DeltaCdc()
        result = pattern.execute("test_data")
        assert result == "test_data"
