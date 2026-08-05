"""Unit tests for the VACUUM pattern."""

import pytest

from src.delta_vacuum import DeltaVacuum, DeltaVacuumConfig


class TestDeltaVacuumConfig:
    """Tests for DeltaVacuumConfig."""

    def test_default_config(self) -> None:
        config = DeltaVacuumConfig()
        assert config.pattern_name == "delta-vacuum"


class TestDeltaVacuum:
    """Tests for DeltaVacuum."""

    def test_init_default_config(self) -> None:
        pattern = DeltaVacuum()
        assert pattern.config.pattern_name == "delta-vacuum"

    def test_init_custom_config(self) -> None:
        config = DeltaVacuumConfig()
        pattern = DeltaVacuum(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DeltaVacuum()
        result = pattern.execute("test_data")
        assert result == "test_data"
