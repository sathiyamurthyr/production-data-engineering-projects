"""Unit tests for the Batch Load pattern."""

import pytest

from src.batch_load import BatchLoad, BatchLoadConfig


class TestBatchLoadConfig:
    """Tests for BatchLoadConfig."""

    def test_default_config(self) -> None:
        config = BatchLoadConfig()
        assert config.pattern_name == "batch-load"


class TestBatchLoad:
    """Tests for BatchLoad."""

    def test_init_default_config(self) -> None:
        pattern = BatchLoad()
        assert pattern.config.pattern_name == "batch-load"

    def test_init_custom_config(self) -> None:
        config = BatchLoadConfig()
        pattern = BatchLoad(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = BatchLoad()
        result = pattern.execute("test_data")
        assert result == "test_data"
