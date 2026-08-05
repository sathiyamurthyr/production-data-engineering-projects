"""Unit tests for the Capacity Planning pattern."""

import pytest

from src.capacity_planning import CapacityPlanning, CapacityPlanningConfig


class TestCapacityPlanningConfig:
    """Tests for CapacityPlanningConfig."""

    def test_default_config(self) -> None:
        config = CapacityPlanningConfig()
        assert config.pattern_name == "capacity-planning"


class TestCapacityPlanning:
    """Tests for CapacityPlanning."""

    def test_init_default_config(self) -> None:
        pattern = CapacityPlanning()
        assert pattern.config.pattern_name == "capacity-planning"

    def test_init_custom_config(self) -> None:
        config = CapacityPlanningConfig()
        pattern = CapacityPlanning(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = CapacityPlanning()
        result = pattern.execute("test_data")
        assert result == "test_data"
