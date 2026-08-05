"""Unit tests for the Retries pattern."""

import pytest

from src.retries import Retries, RetriesConfig


class TestRetriesConfig:
    """Tests for RetriesConfig."""

    def test_default_config(self) -> None:
        config = RetriesConfig()
        assert config.pattern_name == "retries"


class TestRetries:
    """Tests for Retries."""

    def test_init_default_config(self) -> None:
        pattern = Retries()
        assert pattern.config.pattern_name == "retries"

    def test_init_custom_config(self) -> None:
        config = RetriesConfig()
        pattern = Retries(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Retries()
        result = pattern.execute("test_data")
        assert result == "test_data"
