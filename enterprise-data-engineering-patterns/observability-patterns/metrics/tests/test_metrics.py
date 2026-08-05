"""Unit tests for the Metrics pattern."""

import pytest

from src.metrics import Metrics, MetricsConfig


class TestMetricsConfig:
    """Tests for MetricsConfig."""

    def test_default_config(self) -> None:
        config = MetricsConfig()
        assert config.pattern_name == "metrics"


class TestMetrics:
    """Tests for Metrics."""

    def test_init_default_config(self) -> None:
        pattern = Metrics()
        assert pattern.config.pattern_name == "metrics"

    def test_init_custom_config(self) -> None:
        config = MetricsConfig()
        pattern = Metrics(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Metrics()
        result = pattern.execute("test_data")
        assert result == "test_data"
