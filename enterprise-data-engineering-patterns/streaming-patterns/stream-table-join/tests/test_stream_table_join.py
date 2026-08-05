"""Unit tests for the Stream-Table Join pattern."""

import pytest

from src.stream_table_join import StreamTableJoin, StreamTableJoinConfig


class TestStreamTableJoinConfig:
    """Tests for StreamTableJoinConfig."""

    def test_default_config(self) -> None:
        config = StreamTableJoinConfig()
        assert config.pattern_name == "stream-table-join"


class TestStreamTableJoin:
    """Tests for StreamTableJoin."""

    def test_init_default_config(self) -> None:
        pattern = StreamTableJoin()
        assert pattern.config.pattern_name == "stream-table-join"

    def test_init_custom_config(self) -> None:
        config = StreamTableJoinConfig()
        pattern = StreamTableJoin(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = StreamTableJoin()
        result = pattern.execute("test_data")
        assert result == "test_data"
