"""Unit tests for the Cost Allocation pattern."""

import pytest

from src.cost_allocation import CostAllocation, CostAllocationConfig


class TestCostAllocationConfig:
    """Tests for CostAllocationConfig."""

    def test_default_config(self) -> None:
        config = CostAllocationConfig()
        assert config.pattern_name == "cost-allocation"


class TestCostAllocation:
    """Tests for CostAllocation."""

    def test_init_default_config(self) -> None:
        pattern = CostAllocation()
        assert pattern.config.pattern_name == "cost-allocation"

    def test_init_custom_config(self) -> None:
        config = CostAllocationConfig()
        pattern = CostAllocation(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = CostAllocation()
        result = pattern.execute("test_data")
        assert result == "test_data"
