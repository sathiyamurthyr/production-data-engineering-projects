"""Unit tests for the Snapshots pattern."""

import pytest

from src.snapshots import Snapshots, SnapshotsConfig


class TestSnapshotsConfig:
    """Tests for SnapshotsConfig."""

    def test_default_config(self) -> None:
        config = SnapshotsConfig()
        assert config.pattern_name == "snapshots"


class TestSnapshots:
    """Tests for Snapshots."""

    def test_init_default_config(self) -> None:
        pattern = Snapshots()
        assert pattern.config.pattern_name == "snapshots"

    def test_init_custom_config(self) -> None:
        config = SnapshotsConfig()
        pattern = Snapshots(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Snapshots()
        result = pattern.execute("test_data")
        assert result == "test_data"
