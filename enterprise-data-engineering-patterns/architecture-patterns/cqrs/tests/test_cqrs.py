"""Unit tests for the CQRS Concepts pattern."""

import pytest

from src.cqrs import Cqrs, CqrsConfig


class TestCqrsConfig:
    """Tests for CqrsConfig."""

    def test_default_config(self) -> None:
        config = CqrsConfig()
        assert config.pattern_name == "cqrs"


class TestCqrs:
    """Tests for Cqrs."""

    def test_init_default_config(self) -> None:
        pattern = Cqrs()
        assert pattern.config.pattern_name == "cqrs"

    def test_init_custom_config(self) -> None:
        config = CqrsConfig()
        pattern = Cqrs(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Cqrs()
        result = pattern.execute("test_data")
        assert result == "test_data"
