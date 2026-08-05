"""Unit tests for the Data Mesh pattern."""

import pytest

from src.data_mesh import DataMesh, DataMeshConfig


class TestDataMeshConfig:
    """Tests for DataMeshConfig."""

    def test_default_config(self) -> None:
        config = DataMeshConfig()
        assert config.pattern_name == "data-mesh"


class TestDataMesh:
    """Tests for DataMesh."""

    def test_init_default_config(self) -> None:
        pattern = DataMesh()
        assert pattern.config.pattern_name == "data-mesh"

    def test_init_custom_config(self) -> None:
        config = DataMeshConfig()
        pattern = DataMesh(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataMesh()
        result = pattern.execute("test_data")
        assert result == "test_data"
