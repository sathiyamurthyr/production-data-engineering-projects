"""Unit tests for the Event Time pattern."""

import pytest

from src.event_time import EventTime, EventTimeConfig


class TestEventTimeConfig:
    """Tests for EventTimeConfig."""

    def test_default_config(self) -> None:
        config = EventTimeConfig()
        assert config.pattern_name == "event-time"


class TestEventTime:
    """Tests for EventTime."""

    def test_init_default_config(self) -> None:
        pattern = EventTime()
        assert pattern.config.pattern_name == "event-time"

    def test_init_custom_config(self) -> None:
        config = EventTimeConfig()
        pattern = EventTime(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = EventTime()
        result = pattern.execute("test_data")
        assert result == "test_data"
