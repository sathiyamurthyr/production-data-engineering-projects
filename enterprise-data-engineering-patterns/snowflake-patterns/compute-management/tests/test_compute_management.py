"""Unit tests for the Compute Management pattern."""

import pytest

from src.compute_management import ComputeManagement, ComputeManagementConfig


class TestComputeManagementConfig:
    """Tests for ComputeManagementConfig."""

    def test_default_config(self) -> None:
        config = ComputeManagementConfig()
        assert config.pattern_name == "compute-management"


class TestComputeManagement:
    """Tests for ComputeManagement."""

    def test_init_default_config(self) -> None:
        pattern = ComputeManagement()
        assert pattern.config.pattern_name == "compute-management"

    def test_init_custom_config(self) -> None:
        config = ComputeManagementConfig()
        pattern = ComputeManagement(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ComputeManagement()
        result = pattern.execute("test_data")
        assert result == "test_data"
