"""Unit tests for the Event Driven pattern."""

import pytest

from src.event_driven import EventDriven, EventDrivenConfig


class TestEventDrivenConfig:
    """Tests for EventDrivenConfig."""

    def test_default_config(self) -> None:
        config = EventDrivenConfig()
        assert config.pattern_name == "event-driven"


class TestEventDriven:
    """Tests for EventDriven."""

    def test_init_default_config(self) -> None:
        pattern = EventDriven()
        assert pattern.config.pattern_name == "event-driven"

    def test_init_custom_config(self) -> None:
        config = EventDrivenConfig()
        pattern = EventDriven(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = EventDriven()
        result = pattern.execute("test_data")
        assert result == "test_data"
