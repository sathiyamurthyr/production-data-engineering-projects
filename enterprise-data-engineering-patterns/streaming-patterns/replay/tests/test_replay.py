"""Unit tests for the Replay pattern."""

import pytest

from src.replay import Replay, ReplayConfig


class TestReplayConfig:
    """Tests for ReplayConfig."""

    def test_default_config(self) -> None:
        config = ReplayConfig()
        assert config.pattern_name == "replay"


class TestReplay:
    """Tests for Replay."""

    def test_init_default_config(self) -> None:
        pattern = Replay()
        assert pattern.config.pattern_name == "replay"

    def test_init_custom_config(self) -> None:
        config = ReplayConfig()
        pattern = Replay(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Replay()
        result = pattern.execute("test_data")
        assert result == "test_data"
