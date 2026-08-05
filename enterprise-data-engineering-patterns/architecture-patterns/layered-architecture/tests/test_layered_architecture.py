"""Unit tests for the Layered Architecture pattern."""

import pytest

from src.layered_architecture import LayeredArchitecture, LayeredArchitectureConfig


class TestLayeredArchitectureConfig:
    """Tests for LayeredArchitectureConfig."""

    def test_default_config(self) -> None:
        config = LayeredArchitectureConfig()
        assert config.pattern_name == "layered-architecture"


class TestLayeredArchitecture:
    """Tests for LayeredArchitecture."""

    def test_init_default_config(self) -> None:
        pattern = LayeredArchitecture()
        assert pattern.config.pattern_name == "layered-architecture"

    def test_init_custom_config(self) -> None:
        config = LayeredArchitectureConfig()
        pattern = LayeredArchitecture(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = LayeredArchitecture()
        result = pattern.execute("test_data")
        assert result == "test_data"
