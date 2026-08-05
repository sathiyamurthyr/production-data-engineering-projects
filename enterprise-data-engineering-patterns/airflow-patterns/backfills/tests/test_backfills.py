"""Unit tests for the Backfills pattern."""

import pytest

from src.backfills import Backfills, BackfillsConfig


class TestBackfillsConfig:
    """Tests for BackfillsConfig."""

    def test_default_config(self) -> None:
        config = BackfillsConfig()
        assert config.pattern_name == "backfills"


class TestBackfills:
    """Tests for Backfills."""

    def test_init_default_config(self) -> None:
        pattern = Backfills()
        assert pattern.config.pattern_name == "backfills"

    def test_init_custom_config(self) -> None:
        config = BackfillsConfig()
        pattern = Backfills(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Backfills()
        result = pattern.execute("test_data")
        assert result == "test_data"
