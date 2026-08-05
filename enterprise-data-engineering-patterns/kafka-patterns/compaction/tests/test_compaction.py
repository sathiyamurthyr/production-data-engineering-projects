"""Unit tests for the Log Compaction pattern."""

import pytest

from src.compaction import Compaction, CompactionConfig


class TestCompactionConfig:
    """Tests for CompactionConfig."""

    def test_default_config(self) -> None:
        config = CompactionConfig()
        assert config.pattern_name == "compaction"


class TestCompaction:
    """Tests for Compaction."""

    def test_init_default_config(self) -> None:
        pattern = Compaction()
        assert pattern.config.pattern_name == "compaction"

    def test_init_custom_config(self) -> None:
        config = CompactionConfig()
        pattern = Compaction(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Compaction()
        result = pattern.execute("test_data")
        assert result == "test_data"
