"""Unit tests for the At Least Once pattern."""

import pytest

from src.at_least_once import AtLeastOnce, AtLeastOnceConfig


class TestAtLeastOnceConfig:
    """Tests for AtLeastOnceConfig."""

    def test_default_config(self) -> None:
        config = AtLeastOnceConfig()
        assert config.pattern_name == "at-least-once"


class TestAtLeastOnce:
    """Tests for AtLeastOnce."""

    def test_init_default_config(self) -> None:
        pattern = AtLeastOnce()
        assert pattern.config.pattern_name == "at-least-once"

    def test_init_custom_config(self) -> None:
        config = AtLeastOnceConfig()
        pattern = AtLeastOnce(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = AtLeastOnce()
        result = pattern.execute("test_data")
        assert result == "test_data"
