"""Unit tests for the Microservices for Data pattern."""

import pytest

from src.microservices_for_data import MicroservicesForData, MicroservicesForDataConfig


class TestMicroservicesForDataConfig:
    """Tests for MicroservicesForDataConfig."""

    def test_default_config(self) -> None:
        config = MicroservicesForDataConfig()
        assert config.pattern_name == "microservices-for-data"


class TestMicroservicesForData:
    """Tests for MicroservicesForData."""

    def test_init_default_config(self) -> None:
        pattern = MicroservicesForData()
        assert pattern.config.pattern_name == "microservices-for-data"

    def test_init_custom_config(self) -> None:
        config = MicroservicesForDataConfig()
        pattern = MicroservicesForData(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = MicroservicesForData()
        result = pattern.execute("test_data")
        assert result == "test_data"
