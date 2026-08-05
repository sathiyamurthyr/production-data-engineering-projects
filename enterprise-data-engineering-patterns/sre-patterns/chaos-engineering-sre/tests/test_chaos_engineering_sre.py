"""Unit tests for the Chaos Engineering pattern."""

import pytest

from src.chaos_engineering_sre import ChaosEngineeringSre, ChaosEngineeringSreConfig


class TestChaosEngineeringSreConfig:
    """Tests for ChaosEngineeringSreConfig."""

    def test_default_config(self) -> None:
        config = ChaosEngineeringSreConfig()
        assert config.pattern_name == "chaos-engineering-sre"


class TestChaosEngineeringSre:
    """Tests for ChaosEngineeringSre."""

    def test_init_default_config(self) -> None:
        pattern = ChaosEngineeringSre()
        assert pattern.config.pattern_name == "chaos-engineering-sre"

    def test_init_custom_config(self) -> None:
        config = ChaosEngineeringSreConfig()
        pattern = ChaosEngineeringSre(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ChaosEngineeringSre()
        result = pattern.execute("test_data")
        assert result == "test_data"
