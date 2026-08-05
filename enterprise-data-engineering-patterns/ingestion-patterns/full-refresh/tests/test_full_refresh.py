"""Unit tests for the Full Refresh pattern."""

import pytest

from src.full_refresh import FullRefresh, FullRefreshConfig


class TestFullRefreshConfig:
    """Tests for FullRefreshConfig."""

    def test_default_config(self) -> None:
        config = FullRefreshConfig()
        assert config.pattern_name == "full-refresh"


class TestFullRefresh:
    """Tests for FullRefresh."""

    def test_init_default_config(self) -> None:
        pattern = FullRefresh()
        assert pattern.config.pattern_name == "full-refresh"

    def test_init_custom_config(self) -> None:
        config = FullRefreshConfig()
        pattern = FullRefresh(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = FullRefresh()
        result = pattern.execute("test_data")
        assert result == "test_data"
