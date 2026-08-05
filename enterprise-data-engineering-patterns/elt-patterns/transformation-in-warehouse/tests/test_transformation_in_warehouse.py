"""Unit tests for the Data Transformation in Warehouse pattern."""

import pytest

from src.transformation_in_warehouse import TransformationInWarehouse, TransformationInWarehouseConfig


class TestTransformationInWarehouseConfig:
    """Tests for TransformationInWarehouseConfig."""

    def test_default_config(self) -> None:
        config = TransformationInWarehouseConfig()
        assert config.pattern_name == "transformation-in-warehouse"


class TestTransformationInWarehouse:
    """Tests for TransformationInWarehouse."""

    def test_init_default_config(self) -> None:
        pattern = TransformationInWarehouse()
        assert pattern.config.pattern_name == "transformation-in-warehouse"

    def test_init_custom_config(self) -> None:
        config = TransformationInWarehouseConfig()
        pattern = TransformationInWarehouse(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = TransformationInWarehouse()
        result = pattern.execute("test_data")
        assert result == "test_data"
