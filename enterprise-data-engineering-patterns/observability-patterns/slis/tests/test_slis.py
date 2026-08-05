"""Unit tests for the SLIs pattern."""

import pytest

from src.slis import Slis, SlisConfig


class TestSlisConfig:
    """Tests for SlisConfig."""

    def test_default_config(self) -> None:
        config = SlisConfig()
        assert config.pattern_name == "slis"


class TestSlis:
    """Tests for Slis."""

    def test_init_default_config(self) -> None:
        pattern = Slis()
        assert pattern.config.pattern_name == "slis"

    def test_init_custom_config(self) -> None:
        config = SlisConfig()
        pattern = Slis(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Slis()
        result = pattern.execute("test_data")
        assert result == "test_data"
