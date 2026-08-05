"""Unit tests for the ELT with Temp Tables pattern."""

import pytest

from src.temp_tables import TempTables, TempTablesConfig


class TestTempTablesConfig:
    """Tests for TempTablesConfig."""

    def test_default_config(self) -> None:
        config = TempTablesConfig()
        assert config.pattern_name == "temp-tables"


class TestTempTables:
    """Tests for TempTables."""

    def test_init_default_config(self) -> None:
        pattern = TempTables()
        assert pattern.config.pattern_name == "temp-tables"

    def test_init_custom_config(self) -> None:
        config = TempTablesConfig()
        pattern = TempTables(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = TempTables()
        result = pattern.execute("test_data")
        assert result == "test_data"
