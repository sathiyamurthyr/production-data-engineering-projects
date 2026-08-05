"""Unit tests for the Clean Architecture pattern."""

import pytest

from src.clean_architecture import CleanArchitecture, CleanArchitectureConfig


class TestCleanArchitectureConfig:
    """Tests for CleanArchitectureConfig."""

    def test_default_config(self) -> None:
        config = CleanArchitectureConfig()
        assert config.pattern_name == "clean-architecture"


class TestCleanArchitecture:
    """Tests for CleanArchitecture."""

    def test_init_default_config(self) -> None:
        pattern = CleanArchitecture()
        assert pattern.config.pattern_name == "clean-architecture"

    def test_init_custom_config(self) -> None:
        config = CleanArchitectureConfig()
        pattern = CleanArchitecture(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = CleanArchitecture()
        result = pattern.execute("test_data")
        assert result == "test_data"
