"""Unit tests for the Snapshot pattern."""

import pytest

from src.snapshot import Snapshot, SnapshotConfig


class TestSnapshotConfig:
    """Tests for SnapshotConfig."""

    def test_default_config(self) -> None:
        config = SnapshotConfig()
        assert config.pattern_name == "snapshot"


class TestSnapshot:
    """Tests for Snapshot."""

    def test_init_default_config(self) -> None:
        pattern = Snapshot()
        assert pattern.config.pattern_name == "snapshot"

    def test_init_custom_config(self) -> None:
        config = SnapshotConfig()
        pattern = Snapshot(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Snapshot()
        result = pattern.execute("test_data")
        assert result == "test_data"
