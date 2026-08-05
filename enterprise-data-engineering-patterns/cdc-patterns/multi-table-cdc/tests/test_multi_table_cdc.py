"""Unit tests for the Multi-table CDC pattern."""

import pytest

from src.multi_table_cdc import MultiTableCdc, MultiTableCdcConfig


class TestMultiTableCdcConfig:
    """Tests for MultiTableCdcConfig."""

    def test_default_config(self) -> None:
        config = MultiTableCdcConfig()
        assert config.pattern_name == "multi-table-cdc"


class TestMultiTableCdc:
    """Tests for MultiTableCdc."""

    def test_init_default_config(self) -> None:
        pattern = MultiTableCdc()
        assert pattern.config.pattern_name == "multi-table-cdc"

    def test_init_custom_config(self) -> None:
        config = MultiTableCdcConfig()
        pattern = MultiTableCdc(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = MultiTableCdc()
        result = pattern.execute("test_data")
        assert result == "test_data"
