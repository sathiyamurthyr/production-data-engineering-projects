"""Unit tests for the Databricks SQL pattern."""

import pytest

from src.databricks_sql import DatabricksSql, DatabricksSqlConfig


class TestDatabricksSqlConfig:
    """Tests for DatabricksSqlConfig."""

    def test_default_config(self) -> None:
        config = DatabricksSqlConfig()
        assert config.pattern_name == "databricks-sql"


class TestDatabricksSql:
    """Tests for DatabricksSql."""

    def test_init_default_config(self) -> None:
        pattern = DatabricksSql()
        assert pattern.config.pattern_name == "databricks-sql"

    def test_init_custom_config(self) -> None:
        config = DatabricksSqlConfig()
        pattern = DatabricksSql(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DatabricksSql()
        result = pattern.execute("test_data")
        assert result == "test_data"
