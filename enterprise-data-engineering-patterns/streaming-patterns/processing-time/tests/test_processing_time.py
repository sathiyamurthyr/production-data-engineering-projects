"""Unit tests for the Processing Time pattern."""

import pytest

from src.processing_time import ProcessingTime, ProcessingTimeConfig


class TestProcessingTimeConfig:
    """Tests for ProcessingTimeConfig."""

    def test_default_config(self) -> None:
        config = ProcessingTimeConfig()
        assert config.pattern_name == "processing-time"


class TestProcessingTime:
    """Tests for ProcessingTime."""

    def test_init_default_config(self) -> None:
        pattern = ProcessingTime()
        assert pattern.config.pattern_name == "processing-time"

    def test_init_custom_config(self) -> None:
        config = ProcessingTimeConfig()
        pattern = ProcessingTime(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ProcessingTime()
        result = pattern.execute("test_data")
        assert result == "test_data"
