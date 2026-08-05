"""Unit tests for the Model Monitoring pattern."""

import pytest

from src.model_monitoring import ModelMonitoring, ModelMonitoringConfig


class TestModelMonitoringConfig:
    """Tests for ModelMonitoringConfig."""

    def test_default_config(self) -> None:
        config = ModelMonitoringConfig()
        assert config.pattern_name == "model-monitoring"


class TestModelMonitoring:
    """Tests for ModelMonitoring."""

    def test_init_default_config(self) -> None:
        pattern = ModelMonitoring()
        assert pattern.config.pattern_name == "model-monitoring"

    def test_init_custom_config(self) -> None:
        config = ModelMonitoringConfig()
        pattern = ModelMonitoring(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ModelMonitoring()
        result = pattern.execute("test_data")
        assert result == "test_data"
