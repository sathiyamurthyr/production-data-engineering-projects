"""Unit tests for the ELT with Materialized Views pattern."""

import pytest

from src.materialized_views import MaterializedViews, MaterializedViewsConfig


class TestMaterializedViewsConfig:
    """Tests for MaterializedViewsConfig."""

    def test_default_config(self) -> None:
        config = MaterializedViewsConfig()
        assert config.pattern_name == "materialized-views"


class TestMaterializedViews:
    """Tests for MaterializedViews."""

    def test_init_default_config(self) -> None:
        pattern = MaterializedViews()
        assert pattern.config.pattern_name == "materialized-views"

    def test_init_custom_config(self) -> None:
        config = MaterializedViewsConfig()
        pattern = MaterializedViews(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = MaterializedViews()
        result = pattern.execute("test_data")
        assert result == "test_data"
