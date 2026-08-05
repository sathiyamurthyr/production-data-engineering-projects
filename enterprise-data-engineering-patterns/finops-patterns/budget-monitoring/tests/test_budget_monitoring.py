"""Unit tests for the Budget Monitoring pattern."""

import pytest

from src.budget_monitoring import BudgetMonitoring, BudgetMonitoringConfig


class TestBudgetMonitoringConfig:
    """Tests for BudgetMonitoringConfig."""

    def test_default_config(self) -> None:
        config = BudgetMonitoringConfig()
        assert config.pattern_name == "budget-monitoring"


class TestBudgetMonitoring:
    """Tests for BudgetMonitoring."""

    def test_init_default_config(self) -> None:
        pattern = BudgetMonitoring()
        assert pattern.config.pattern_name == "budget-monitoring"

    def test_init_custom_config(self) -> None:
        config = BudgetMonitoringConfig()
        pattern = BudgetMonitoring(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = BudgetMonitoring()
        result = pattern.execute("test_data")
        assert result == "test_data"
