"""Unit tests for the Streaming Aggregation pattern."""

import pytest

from src.streaming_aggregation import StreamingAggregation, StreamingAggregationConfig


class TestStreamingAggregationConfig:
    """Tests for StreamingAggregationConfig."""

    def test_default_config(self) -> None:
        config = StreamingAggregationConfig()
        assert config.pattern_name == "streaming-aggregation"


class TestStreamingAggregation:
    """Tests for StreamingAggregation."""

    def test_init_default_config(self) -> None:
        pattern = StreamingAggregation()
        assert pattern.config.pattern_name == "streaming-aggregation"

    def test_init_custom_config(self) -> None:
        config = StreamingAggregationConfig()
        pattern = StreamingAggregation(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = StreamingAggregation()
        result = pattern.execute("test_data")
        assert result == "test_data"
