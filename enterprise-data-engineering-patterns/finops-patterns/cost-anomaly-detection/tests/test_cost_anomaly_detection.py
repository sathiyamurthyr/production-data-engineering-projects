"""Unit tests for the Cost Anomaly Detection pattern."""

import pytest

from src.cost_anomaly_detection import CostAnomalyDetection, CostAnomalyDetectionConfig


class TestCostAnomalyDetectionConfig:
    """Tests for CostAnomalyDetectionConfig."""

    def test_default_config(self) -> None:
        config = CostAnomalyDetectionConfig()
        assert config.pattern_name == "cost-anomaly-detection"


class TestCostAnomalyDetection:
    """Tests for CostAnomalyDetection."""

    def test_init_default_config(self) -> None:
        pattern = CostAnomalyDetection()
        assert pattern.config.pattern_name == "cost-anomaly-detection"

    def test_init_custom_config(self) -> None:
        config = CostAnomalyDetectionConfig()
        pattern = CostAnomalyDetection(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = CostAnomalyDetection()
        result = pattern.execute("test_data")
        assert result == "test_data"
