"""Unit tests for the Incremental Load pattern."""

import pytest

from src.incremental_load import IncrementalLoad, IncrementalLoadConfig


class TestIncrementalLoadConfig:
    """Tests for IncrementalLoadConfig."""

    def test_default_config(self) -> None:
        config = IncrementalLoadConfig()
        assert config.pattern_name == "incremental-load"


class TestIncrementalLoad:
    """Tests for IncrementalLoad."""

    def test_init_default_config(self) -> None:
        pattern = IncrementalLoad()
        assert pattern.config.pattern_name == "incremental-load"

    def test_init_custom_config(self) -> None:
        config = IncrementalLoadConfig()
        pattern = IncrementalLoad(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = IncrementalLoad()
        result = pattern.execute("test_data")
        assert result == "test_data"
