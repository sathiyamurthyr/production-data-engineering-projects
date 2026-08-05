"""Unit tests for the Trigger-based CDC pattern."""

import pytest

from src.trigger_based_cdc import TriggerBasedCdc, TriggerBasedCdcConfig


class TestTriggerBasedCdcConfig:
    """Tests for TriggerBasedCdcConfig."""

    def test_default_config(self) -> None:
        config = TriggerBasedCdcConfig()
        assert config.pattern_name == "trigger-based-cdc"


class TestTriggerBasedCdc:
    """Tests for TriggerBasedCdc."""

    def test_init_default_config(self) -> None:
        pattern = TriggerBasedCdc()
        assert pattern.config.pattern_name == "trigger-based-cdc"

    def test_init_custom_config(self) -> None:
        config = TriggerBasedCdcConfig()
        pattern = TriggerBasedCdc(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = TriggerBasedCdc()
        result = pattern.execute("test_data")
        assert result == "test_data"
