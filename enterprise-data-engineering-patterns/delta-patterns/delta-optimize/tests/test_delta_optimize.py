"""Unit tests for the OPTIMIZE pattern."""

import pytest

from src.delta_optimize import DeltaOptimize, DeltaOptimizeConfig


class TestDeltaOptimizeConfig:
    """Tests for DeltaOptimizeConfig."""

    def test_default_config(self) -> None:
        config = DeltaOptimizeConfig()
        assert config.pattern_name == "delta-optimize"


class TestDeltaOptimize:
    """Tests for DeltaOptimize."""

    def test_init_default_config(self) -> None:
        pattern = DeltaOptimize()
        assert pattern.config.pattern_name == "delta-optimize"

    def test_init_custom_config(self) -> None:
        config = DeltaOptimizeConfig()
        pattern = DeltaOptimize(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DeltaOptimize()
        result = pattern.execute("test_data")
        assert result == "test_data"
