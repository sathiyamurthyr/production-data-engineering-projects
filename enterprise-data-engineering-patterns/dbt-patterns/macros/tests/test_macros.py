"""Unit tests for the Macros pattern."""

import pytest

from src.macros import Macros, MacrosConfig


class TestMacrosConfig:
    """Tests for MacrosConfig."""

    def test_default_config(self) -> None:
        config = MacrosConfig()
        assert config.pattern_name == "macros"


class TestMacros:
    """Tests for Macros."""

    def test_init_default_config(self) -> None:
        pattern = Macros()
        assert pattern.config.pattern_name == "macros"

    def test_init_custom_config(self) -> None:
        config = MacrosConfig()
        pattern = Macros(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Macros()
        result = pattern.execute("test_data")
        assert result == "test_data"
