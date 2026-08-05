"""Unit tests for the SCD Type 3 pattern."""

import pytest

from src.scd_type_3 import ScdType3, ScdType3Config


class TestScdType3Config:
    """Tests for ScdType3Config."""

    def test_default_config(self) -> None:
        config = ScdType3Config()
        assert config.pattern_name == "scd-type-3"


class TestScdType3:
    """Tests for ScdType3."""

    def test_init_default_config(self) -> None:
        pattern = ScdType3()
        assert pattern.config.pattern_name == "scd-type-3"

    def test_init_custom_config(self) -> None:
        config = ScdType3Config()
        pattern = ScdType3(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ScdType3()
        result = pattern.execute("test_data")
        assert result == "test_data"
