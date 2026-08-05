"""Unit tests for the Anomaly Detection pattern."""

import pytest

from src.anomaly_detection import AnomalyDetection, AnomalyDetectionConfig


class TestAnomalyDetectionConfig:
    """Tests for AnomalyDetectionConfig."""

    def test_default_config(self) -> None:
        config = AnomalyDetectionConfig()
        assert config.pattern_name == "anomaly-detection"


class TestAnomalyDetection:
    """Tests for AnomalyDetection."""

    def test_init_default_config(self) -> None:
        pattern = AnomalyDetection()
        assert pattern.config.pattern_name == "anomaly-detection"

    def test_init_custom_config(self) -> None:
        config = AnomalyDetectionConfig()
        pattern = AnomalyDetection(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = AnomalyDetection()
        result = pattern.execute("test_data")
        assert result == "test_data"
