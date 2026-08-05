"""Unit tests for the ELT with CTAS pattern."""

import pytest

from src.ctas import Ctas, CtasConfig


class TestCtasConfig:
    """Tests for CtasConfig."""

    def test_default_config(self) -> None:
        config = CtasConfig()
        assert config.pattern_name == "ctas"


class TestCtas:
    """Tests for Ctas."""

    def test_init_default_config(self) -> None:
        pattern = Ctas()
        assert pattern.config.pattern_name == "ctas"

    def test_init_custom_config(self) -> None:
        config = CtasConfig()
        pattern = Ctas(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Ctas()
        result = pattern.execute("test_data")
        assert result == "test_data"
