"""Unit tests for the Vector Storage pattern."""

import pytest

from src.vector_storage import VectorStorage, VectorStorageConfig


class TestVectorStorageConfig:
    """Tests for VectorStorageConfig."""

    def test_default_config(self) -> None:
        config = VectorStorageConfig()
        assert config.pattern_name == "vector-storage"


class TestVectorStorage:
    """Tests for VectorStorage."""

    def test_init_default_config(self) -> None:
        pattern = VectorStorage()
        assert pattern.config.pattern_name == "vector-storage"

    def test_init_custom_config(self) -> None:
        config = VectorStorageConfig()
        pattern = VectorStorage(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = VectorStorage()
        result = pattern.execute("test_data")
        assert result == "test_data"
