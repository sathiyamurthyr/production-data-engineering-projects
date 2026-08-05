"""Unit tests for the Runbooks pattern."""

import pytest

from src.runbooks import Runbooks, RunbooksConfig


class TestRunbooksConfig:
    """Tests for RunbooksConfig."""

    def test_default_config(self) -> None:
        config = RunbooksConfig()
        assert config.pattern_name == "runbooks"


class TestRunbooks:
    """Tests for Runbooks."""

    def test_init_default_config(self) -> None:
        pattern = Runbooks()
        assert pattern.config.pattern_name == "runbooks"

    def test_init_custom_config(self) -> None:
        config = RunbooksConfig()
        pattern = Runbooks(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Runbooks()
        result = pattern.execute("test_data")
        assert result == "test_data"
