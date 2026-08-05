"""Unit tests for the ZORDER pattern."""

import pytest

from src.zorder import Zorder, ZorderConfig


class TestZorderConfig:
    """Tests for ZorderConfig."""

    def test_default_config(self) -> None:
        config = ZorderConfig()
        assert config.pattern_name == "zorder"


class TestZorder:
    """Tests for Zorder."""

    def test_init_default_config(self) -> None:
        pattern = Zorder()
        assert pattern.config.pattern_name == "zorder"

    def test_init_custom_config(self) -> None:
        config = ZorderConfig()
        pattern = Zorder(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Zorder()
        result = pattern.execute("test_data")
        assert result == "test_data"
