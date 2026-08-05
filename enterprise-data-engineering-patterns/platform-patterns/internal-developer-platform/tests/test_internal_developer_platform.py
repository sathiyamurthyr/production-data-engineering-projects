"""Unit tests for the Internal Developer Platform pattern."""

import pytest

from src.internal_developer_platform import InternalDeveloperPlatform, InternalDeveloperPlatformConfig


class TestInternalDeveloperPlatformConfig:
    """Tests for InternalDeveloperPlatformConfig."""

    def test_default_config(self) -> None:
        config = InternalDeveloperPlatformConfig()
        assert config.pattern_name == "internal-developer-platform"


class TestInternalDeveloperPlatform:
    """Tests for InternalDeveloperPlatform."""

    def test_init_default_config(self) -> None:
        pattern = InternalDeveloperPlatform()
        assert pattern.config.pattern_name == "internal-developer-platform"

    def test_init_custom_config(self) -> None:
        config = InternalDeveloperPlatformConfig()
        pattern = InternalDeveloperPlatform(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = InternalDeveloperPlatform()
        result = pattern.execute("test_data")
        assert result == "test_data"
