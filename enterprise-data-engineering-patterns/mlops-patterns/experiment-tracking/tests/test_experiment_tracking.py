"""Unit tests for the Experiment Tracking pattern."""

import pytest

from src.experiment_tracking import ExperimentTracking, ExperimentTrackingConfig


class TestExperimentTrackingConfig:
    """Tests for ExperimentTrackingConfig."""

    def test_default_config(self) -> None:
        config = ExperimentTrackingConfig()
        assert config.pattern_name == "experiment-tracking"


class TestExperimentTracking:
    """Tests for ExperimentTracking."""

    def test_init_default_config(self) -> None:
        pattern = ExperimentTracking()
        assert pattern.config.pattern_name == "experiment-tracking"

    def test_init_custom_config(self) -> None:
        config = ExperimentTrackingConfig()
        pattern = ExperimentTracking(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ExperimentTracking()
        result = pattern.execute("test_data")
        assert result == "test_data"
