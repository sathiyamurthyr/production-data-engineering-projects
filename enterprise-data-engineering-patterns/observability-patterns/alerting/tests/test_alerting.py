"""Unit tests for the Alerting pattern."""

import pytest

from src.alerting import Alerting, AlertingConfig


class TestAlertingConfig:
    """Tests for AlertingConfig."""

    def test_default_config(self) -> None:
        config = AlertingConfig()
        assert config.pattern_name == "alerting"


class TestAlerting:
    """Tests for Alerting."""

    def test_init_default_config(self) -> None:
        pattern = Alerting()
        assert pattern.config.pattern_name == "alerting"

    def test_init_custom_config(self) -> None:
        config = AlertingConfig()
        pattern = Alerting(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Alerting()
        result = pattern.execute("test_data")
        assert result == "test_data"
