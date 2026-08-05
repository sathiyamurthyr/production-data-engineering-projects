"""Unit tests for the SLAs pattern."""

import pytest

from src.slas import Slas, SlasConfig


class TestSlasConfig:
    """Tests for SlasConfig."""

    def test_default_config(self) -> None:
        config = SlasConfig()
        assert config.pattern_name == "slas"


class TestSlas:
    """Tests for Slas."""

    def test_init_default_config(self) -> None:
        pattern = Slas()
        assert pattern.config.pattern_name == "slas"

    def test_init_custom_config(self) -> None:
        config = SlasConfig()
        pattern = Slas(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Slas()
        result = pattern.execute("test_data")
        assert result == "test_data"
