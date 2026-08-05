"""Unit tests for the Data Quality Monitoring pattern."""

import pytest

from src.data_quality_monitoring import DataQualityMonitoring, DataQualityMonitoringConfig


class TestDataQualityMonitoringConfig:
    """Tests for DataQualityMonitoringConfig."""

    def test_default_config(self) -> None:
        config = DataQualityMonitoringConfig()
        assert config.pattern_name == "data-quality-monitoring"


class TestDataQualityMonitoring:
    """Tests for DataQualityMonitoring."""

    def test_init_default_config(self) -> None:
        pattern = DataQualityMonitoring()
        assert pattern.config.pattern_name == "data-quality-monitoring"

    def test_init_custom_config(self) -> None:
        config = DataQualityMonitoringConfig()
        pattern = DataQualityMonitoring(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataQualityMonitoring()
        result = pattern.execute("test_data")
        assert result == "test_data"
