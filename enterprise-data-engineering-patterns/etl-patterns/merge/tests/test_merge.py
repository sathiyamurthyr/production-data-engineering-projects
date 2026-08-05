"""Unit tests for the Merge pattern."""

import pytest

from src.merge import Merge, MergeConfig


class TestMergeConfig:
    """Tests for MergeConfig."""

    def test_default_config(self) -> None:
        config = MergeConfig()
        assert config.pattern_name == "merge"


class TestMerge:
    """Tests for Merge."""

    def test_init_default_config(self) -> None:
        pattern = Merge()
        assert pattern.config.pattern_name == "merge"

    def test_init_custom_config(self) -> None:
        config = MergeConfig()
        pattern = Merge(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Merge()
        result = pattern.execute("test_data")
        assert result == "test_data"
