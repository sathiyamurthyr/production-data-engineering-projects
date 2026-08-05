"""Unit tests for the Auto Loader pattern."""

import pytest

from src.autoloader import Autoloader, AutoloaderConfig


class TestAutoloaderConfig:
    """Tests for AutoloaderConfig."""

    def test_default_config(self) -> None:
        config = AutoloaderConfig()
        assert config.pattern_name == "autoloader"


class TestAutoloader:
    """Tests for Autoloader."""

    def test_init_default_config(self) -> None:
        pattern = Autoloader()
        assert pattern.config.pattern_name == "autoloader"

    def test_init_custom_config(self) -> None:
        config = AutoloaderConfig()
        pattern = Autoloader(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Autoloader()
        result = pattern.execute("test_data")
        assert result == "test_data"
