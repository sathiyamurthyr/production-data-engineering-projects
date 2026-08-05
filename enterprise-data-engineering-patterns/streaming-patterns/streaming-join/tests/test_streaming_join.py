"""Unit tests for the Streaming Join pattern."""

import pytest

from src.streaming_join import StreamingJoin, StreamingJoinConfig


class TestStreamingJoinConfig:
    """Tests for StreamingJoinConfig."""

    def test_default_config(self) -> None:
        config = StreamingJoinConfig()
        assert config.pattern_name == "streaming-join"


class TestStreamingJoin:
    """Tests for StreamingJoin."""

    def test_init_default_config(self) -> None:
        pattern = StreamingJoin()
        assert pattern.config.pattern_name == "streaming-join"

    def test_init_custom_config(self) -> None:
        config = StreamingJoinConfig()
        pattern = StreamingJoin(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = StreamingJoin()
        result = pattern.execute("test_data")
        assert result == "test_data"
