"""Unit tests for the Databricks Jobs pattern."""

import pytest

from src.databricks_jobs import DatabricksJobs, DatabricksJobsConfig


class TestDatabricksJobsConfig:
    """Tests for DatabricksJobsConfig."""

    def test_default_config(self) -> None:
        config = DatabricksJobsConfig()
        assert config.pattern_name == "databricks-jobs"


class TestDatabricksJobs:
    """Tests for DatabricksJobs."""

    def test_init_default_config(self) -> None:
        pattern = DatabricksJobs()
        assert pattern.config.pattern_name == "databricks-jobs"

    def test_init_custom_config(self) -> None:
        config = DatabricksJobsConfig()
        pattern = DatabricksJobs(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DatabricksJobs()
        result = pattern.execute("test_data")
        assert result == "test_data"
