"""Unit tests for the Unity Catalog pattern."""

import pytest

from src.unity_catalog import UnityCatalog, UnityCatalogConfig


class TestUnityCatalogConfig:
    """Tests for UnityCatalogConfig."""

    def test_default_config(self) -> None:
        config = UnityCatalogConfig()
        assert config.pattern_name == "unity-catalog"


class TestUnityCatalog:
    """Tests for UnityCatalog."""

    def test_init_default_config(self) -> None:
        pattern = UnityCatalog()
        assert pattern.config.pattern_name == "unity-catalog"

    def test_init_custom_config(self) -> None:
        config = UnityCatalogConfig()
        pattern = UnityCatalog(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = UnityCatalog()
        result = pattern.execute("test_data")
        assert result == "test_data"
