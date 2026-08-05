"""Unit tests for the Data Lineage pattern."""

import pytest

from src.data_lineage import DataLineage, DataLineageConfig


class TestDataLineageConfig:
    """Tests for DataLineageConfig."""

    def test_default_config(self) -> None:
        config = DataLineageConfig()
        assert config.pattern_name == "data-lineage"


class TestDataLineage:
    """Tests for DataLineage."""

    def test_init_default_config(self) -> None:
        pattern = DataLineage()
        assert pattern.config.pattern_name == "data-lineage"

    def test_init_custom_config(self) -> None:
        config = DataLineageConfig()
        pattern = DataLineage(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataLineage()
        result = pattern.execute("test_data")
        assert result == "test_data"
