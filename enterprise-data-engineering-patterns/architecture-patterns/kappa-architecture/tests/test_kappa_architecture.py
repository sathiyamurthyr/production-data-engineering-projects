"""Unit tests for the Kappa Architecture pattern."""

import pytest

from src.kappa_architecture import KappaArchitecture, KappaArchitectureConfig


class TestKappaArchitectureConfig:
    """Tests for KappaArchitectureConfig."""

    def test_default_config(self) -> None:
        config = KappaArchitectureConfig()
        assert config.pattern_name == "kappa-architecture"


class TestKappaArchitecture:
    """Tests for KappaArchitecture."""

    def test_init_default_config(self) -> None:
        pattern = KappaArchitecture()
        assert pattern.config.pattern_name == "kappa-architecture"

    def test_init_custom_config(self) -> None:
        config = KappaArchitectureConfig()
        pattern = KappaArchitecture(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = KappaArchitecture()
        result = pattern.execute("test_data")
        assert result == "test_data"
