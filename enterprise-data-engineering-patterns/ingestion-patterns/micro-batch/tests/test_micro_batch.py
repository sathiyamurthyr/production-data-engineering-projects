"""Unit tests for the Micro Batch pattern."""

import pytest

from src.micro_batch import MicroBatch, MicroBatchConfig


class TestMicroBatchConfig:
    """Tests for MicroBatchConfig."""

    def test_default_config(self) -> None:
        config = MicroBatchConfig()
        assert config.pattern_name == "micro-batch"


class TestMicroBatch:
    """Tests for MicroBatch."""

    def test_init_default_config(self) -> None:
        pattern = MicroBatch()
        assert pattern.config.pattern_name == "micro-batch"

    def test_init_custom_config(self) -> None:
        config = MicroBatchConfig()
        pattern = MicroBatch(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = MicroBatch()
        result = pattern.execute("test_data")
        assert result == "test_data"
