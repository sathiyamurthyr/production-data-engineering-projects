"""Unit tests for the CDC with Ordering pattern."""

import pytest

from src.cdc_ordering import CdcOrdering, CdcOrderingConfig


class TestCdcOrderingConfig:
    """Tests for CdcOrderingConfig."""

    def test_default_config(self) -> None:
        config = CdcOrderingConfig()
        assert config.pattern_name == "cdc-ordering"


class TestCdcOrdering:
    """Tests for CdcOrdering."""

    def test_init_default_config(self) -> None:
        pattern = CdcOrdering()
        assert pattern.config.pattern_name == "cdc-ordering"

    def test_init_custom_config(self) -> None:
        config = CdcOrderingConfig()
        pattern = CdcOrdering(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = CdcOrdering()
        result = pattern.execute("test_data")
        assert result == "test_data"
