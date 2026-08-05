"""Unit tests for the Tests pattern."""

import pytest

from src.tests import Tests, TestsConfig


class TestTestsConfig:
    """Tests for TestsConfig."""

    def test_default_config(self) -> None:
        config = TestsConfig()
        assert config.pattern_name == "tests"


class TestTests:
    """Tests for Tests."""

    def test_init_default_config(self) -> None:
        pattern = Tests()
        assert pattern.config.pattern_name == "tests"

    def test_init_custom_config(self) -> None:
        config = TestsConfig()
        pattern = Tests(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Tests()
        result = pattern.execute("test_data")
        assert result == "test_data"
