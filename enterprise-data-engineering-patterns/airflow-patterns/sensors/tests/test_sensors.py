"""Unit tests for the Sensors pattern."""

import pytest

from src.sensors import Sensors, SensorsConfig


class TestSensorsConfig:
    """Tests for SensorsConfig."""

    def test_default_config(self) -> None:
        config = SensorsConfig()
        assert config.pattern_name == "sensors"


class TestSensors:
    """Tests for Sensors."""

    def test_init_default_config(self) -> None:
        pattern = Sensors()
        assert pattern.config.pattern_name == "sensors"

    def test_init_custom_config(self) -> None:
        config = SensorsConfig()
        pattern = Sensors(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Sensors()
        result = pattern.execute("test_data")
        assert result == "test_data"
