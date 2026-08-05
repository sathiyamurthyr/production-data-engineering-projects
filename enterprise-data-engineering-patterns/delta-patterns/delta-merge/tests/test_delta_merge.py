"""Unit tests for the MERGE pattern."""

import pytest

from src.delta_merge import DeltaMerge, DeltaMergeConfig


class TestDeltaMergeConfig:
    """Tests for DeltaMergeConfig."""

    def test_default_config(self) -> None:
        config = DeltaMergeConfig()
        assert config.pattern_name == "delta-merge"


class TestDeltaMerge:
    """Tests for DeltaMerge."""

    def test_init_default_config(self) -> None:
        pattern = DeltaMerge()
        assert pattern.config.pattern_name == "delta-merge"

    def test_init_custom_config(self) -> None:
        config = DeltaMergeConfig()
        pattern = DeltaMerge(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DeltaMerge()
        result = pattern.execute("test_data")
        assert result == "test_data"
