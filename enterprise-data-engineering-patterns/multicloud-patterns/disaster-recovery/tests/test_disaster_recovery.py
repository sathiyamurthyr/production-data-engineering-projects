"""Unit tests for the Disaster Recovery pattern."""

import pytest

from src.disaster_recovery import DisasterRecovery, DisasterRecoveryConfig


class TestDisasterRecoveryConfig:
    """Tests for DisasterRecoveryConfig."""

    def test_default_config(self) -> None:
        config = DisasterRecoveryConfig()
        assert config.pattern_name == "disaster-recovery"


class TestDisasterRecovery:
    """Tests for DisasterRecovery."""

    def test_init_default_config(self) -> None:
        pattern = DisasterRecovery()
        assert pattern.config.pattern_name == "disaster-recovery"

    def test_init_custom_config(self) -> None:
        config = DisasterRecoveryConfig()
        pattern = DisasterRecovery(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DisasterRecovery()
        result = pattern.execute("test_data")
        assert result == "test_data"
