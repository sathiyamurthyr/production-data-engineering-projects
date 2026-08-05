"""Unit tests for the SLOs pattern."""

import pytest

from src.slos import Slos, SlosConfig


class TestSlosConfig:
    """Tests for SlosConfig."""

    def test_default_config(self) -> None:
        config = SlosConfig()
        assert config.pattern_name == "slos"


class TestSlos:
    """Tests for Slos."""

    def test_init_default_config(self) -> None:
        pattern = Slos()
        assert pattern.config.pattern_name == "slos"

    def test_init_custom_config(self) -> None:
        config = SlosConfig()
        pattern = Slos(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Slos()
        result = pattern.execute("test_data")
        assert result == "test_data"
