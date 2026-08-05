"""Unit tests for the Lakehouse pattern."""

import pytest

from src.lakehouse import Lakehouse, LakehouseConfig


class TestLakehouseConfig:
    """Tests for LakehouseConfig."""

    def test_default_config(self) -> None:
        config = LakehouseConfig()
        assert config.pattern_name == "lakehouse"


class TestLakehouse:
    """Tests for Lakehouse."""

    def test_init_default_config(self) -> None:
        pattern = Lakehouse()
        assert pattern.config.pattern_name == "lakehouse"

    def test_init_custom_config(self) -> None:
        config = LakehouseConfig()
        pattern = Lakehouse(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Lakehouse()
        result = pattern.execute("test_data")
        assert result == "test_data"
