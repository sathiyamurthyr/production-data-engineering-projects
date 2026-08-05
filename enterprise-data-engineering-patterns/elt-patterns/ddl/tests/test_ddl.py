"""Unit tests for the ELT with DDL pattern."""

import pytest

from src.ddl import Ddl, DdlConfig


class TestDdlConfig:
    """Tests for DdlConfig."""

    def test_default_config(self) -> None:
        config = DdlConfig()
        assert config.pattern_name == "ddl"


class TestDdl:
    """Tests for Ddl."""

    def test_init_default_config(self) -> None:
        pattern = Ddl()
        assert pattern.config.pattern_name == "ddl"

    def test_init_custom_config(self) -> None:
        config = DdlConfig()
        pattern = Ddl(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Ddl()
        result = pattern.execute("test_data")
        assert result == "test_data"
