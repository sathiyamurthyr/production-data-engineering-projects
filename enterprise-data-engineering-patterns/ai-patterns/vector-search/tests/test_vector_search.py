"""Unit tests for the Vector Search pattern."""

import pytest

from src.vector_search import VectorSearch, VectorSearchConfig


class TestVectorSearchConfig:
    """Tests for VectorSearchConfig."""

    def test_default_config(self) -> None:
        config = VectorSearchConfig()
        assert config.pattern_name == "vector-search"


class TestVectorSearch:
    """Tests for VectorSearch."""

    def test_init_default_config(self) -> None:
        pattern = VectorSearch()
        assert pattern.config.pattern_name == "vector-search"

    def test_init_custom_config(self) -> None:
        config = VectorSearchConfig()
        pattern = VectorSearch(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = VectorSearch()
        result = pattern.execute("test_data")
        assert result == "test_data"
