"""Unit tests for the ELT with Views pattern."""

import pytest

from src.views import Views, ViewsConfig


class TestViewsConfig:
    """Tests for ViewsConfig."""

    def test_default_config(self) -> None:
        config = ViewsConfig()
        assert config.pattern_name == "views"


class TestViews:
    """Tests for Views."""

    def test_init_default_config(self) -> None:
        pattern = Views()
        assert pattern.config.pattern_name == "views"

    def test_init_custom_config(self) -> None:
        config = ViewsConfig()
        pattern = Views(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Views()
        result = pattern.execute("test_data")
        assert result == "test_data"
