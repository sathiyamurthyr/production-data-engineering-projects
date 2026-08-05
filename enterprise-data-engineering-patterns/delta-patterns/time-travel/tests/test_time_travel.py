"""Unit tests for the Time Travel pattern."""

import pytest

from src.time_travel import TimeTravel, TimeTravelConfig


class TestTimeTravelConfig:
    """Tests for TimeTravelConfig."""

    def test_default_config(self) -> None:
        config = TimeTravelConfig()
        assert config.pattern_name == "time-travel"


class TestTimeTravel:
    """Tests for TimeTravel."""

    def test_init_default_config(self) -> None:
        pattern = TimeTravel()
        assert pattern.config.pattern_name == "time-travel"

    def test_init_custom_config(self) -> None:
        config = TimeTravelConfig()
        pattern = TimeTravel(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = TimeTravel()
        result = pattern.execute("test_data")
        assert result == "test_data"
