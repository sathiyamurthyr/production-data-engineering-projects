"""Unit tests for the Enterprise Data Warehouse pattern."""

import pytest

from src.warehouse import Warehouse, WarehouseConfig


class TestWarehouseConfig:
    """Tests for WarehouseConfig."""

    def test_default_config(self) -> None:
        config = WarehouseConfig()
        assert config.pattern_name == "warehouse"


class TestWarehouse:
    """Tests for Warehouse."""

    def test_init_default_config(self) -> None:
        pattern = Warehouse()
        assert pattern.config.pattern_name == "warehouse"

    def test_init_custom_config(self) -> None:
        config = WarehouseConfig()
        pattern = Warehouse(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Warehouse()
        result = pattern.execute("test_data")
        assert result == "test_data"
