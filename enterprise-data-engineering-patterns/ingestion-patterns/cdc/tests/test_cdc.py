"""Unit tests for the Change Data Capture pattern."""

import pytest

from src.cdc import Cdc, CdcConfig


class TestCdcConfig:
    """Tests for CdcConfig."""

    def test_default_config(self) -> None:
        config = CdcConfig()
        assert config.pattern_name == "cdc"


class TestCdc:
    """Tests for Cdc."""

    def test_init_default_config(self) -> None:
        pattern = Cdc()
        assert pattern.config.pattern_name == "cdc"

    def test_init_custom_config(self) -> None:
        config = CdcConfig()
        pattern = Cdc(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Cdc()
        result = pattern.execute("test_data")
        assert result == "test_data"
