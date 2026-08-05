"""Unit tests for the Branching pattern."""

import pytest

from src.branching import Branching, BranchingConfig


class TestBranchingConfig:
    """Tests for BranchingConfig."""

    def test_default_config(self) -> None:
        config = BranchingConfig()
        assert config.pattern_name == "branching"


class TestBranching:
    """Tests for Branching."""

    def test_init_default_config(self) -> None:
        pattern = Branching()
        assert pattern.config.pattern_name == "branching"

    def test_init_custom_config(self) -> None:
        config = BranchingConfig()
        pattern = Branching(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Branching()
        result = pattern.execute("test_data")
        assert result == "test_data"
