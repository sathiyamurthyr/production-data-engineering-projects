"""Unit tests for the Incremental ELT pattern."""

import pytest

from src.incremental_elt import IncrementalElt, IncrementalEltConfig


class TestIncrementalEltConfig:
    """Tests for IncrementalEltConfig."""

    def test_default_config(self) -> None:
        config = IncrementalEltConfig()
        assert config.pattern_name == "incremental-elt"


class TestIncrementalElt:
    """Tests for IncrementalElt."""

    def test_init_default_config(self) -> None:
        pattern = IncrementalElt()
        assert pattern.config.pattern_name == "incremental-elt"

    def test_init_custom_config(self) -> None:
        config = IncrementalEltConfig()
        pattern = IncrementalElt(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = IncrementalElt()
        result = pattern.execute("test_data")
        assert result == "test_data"
