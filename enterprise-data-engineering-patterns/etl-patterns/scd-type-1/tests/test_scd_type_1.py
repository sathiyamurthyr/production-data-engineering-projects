"""Unit tests for the SCD Type 1 pattern."""

import pytest

from src.scd_type_1 import ScdType1, ScdType1Config


class TestScdType1Config:
    """Tests for ScdType1Config."""

    def test_default_config(self) -> None:
        config = ScdType1Config()
        assert config.pattern_name == "scd-type-1"


class TestScdType1:
    """Tests for ScdType1."""

    def test_init_default_config(self) -> None:
        pattern = ScdType1()
        assert pattern.config.pattern_name == "scd-type-1"

    def test_init_custom_config(self) -> None:
        config = ScdType1Config()
        pattern = ScdType1(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ScdType1()
        result = pattern.execute("test_data")
        assert result == "test_data"
