"""Unit tests for the Streaming Ingestion pattern."""

import pytest

from src.streaming_ingestion import StreamingIngestion, StreamingIngestionConfig


class TestStreamingIngestionConfig:
    """Tests for StreamingIngestionConfig."""

    def test_default_config(self) -> None:
        config = StreamingIngestionConfig()
        assert config.pattern_name == "streaming-ingestion"


class TestStreamingIngestion:
    """Tests for StreamingIngestion."""

    def test_init_default_config(self) -> None:
        pattern = StreamingIngestion()
        assert pattern.config.pattern_name == "streaming-ingestion"

    def test_init_custom_config(self) -> None:
        config = StreamingIngestionConfig()
        pattern = StreamingIngestion(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = StreamingIngestion()
        result = pattern.execute("test_data")
        assert result == "test_data"
