"""Unit tests for the Streams pattern."""

import pytest

from src.streams import Streams, StreamsConfig


class TestStreamsConfig:
    """Tests for StreamsConfig."""

    def test_default_config(self) -> None:
        config = StreamsConfig()
        assert config.pattern_name == "streams"


class TestStreams:
    """Tests for Streams."""

    def test_init_default_config(self) -> None:
        pattern = Streams()
        assert pattern.config.pattern_name == "streams"

    def test_init_custom_config(self) -> None:
        config = StreamsConfig()
        pattern = Streams(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Streams()
        result = pattern.execute("test_data")
        assert result == "test_data"
