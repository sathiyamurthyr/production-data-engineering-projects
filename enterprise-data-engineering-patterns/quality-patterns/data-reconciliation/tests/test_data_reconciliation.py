"""Unit tests for the Data Reconciliation pattern."""

import pytest

from src.data_reconciliation import DataReconciliation, DataReconciliationConfig


class TestDataReconciliationConfig:
    """Tests for DataReconciliationConfig."""

    def test_default_config(self) -> None:
        config = DataReconciliationConfig()
        assert config.pattern_name == "data-reconciliation"


class TestDataReconciliation:
    """Tests for DataReconciliation."""

    def test_init_default_config(self) -> None:
        pattern = DataReconciliation()
        assert pattern.config.pattern_name == "data-reconciliation"

    def test_init_custom_config(self) -> None:
        config = DataReconciliationConfig()
        pattern = DataReconciliation(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataReconciliation()
        result = pattern.execute("test_data")
        assert result == "test_data"
