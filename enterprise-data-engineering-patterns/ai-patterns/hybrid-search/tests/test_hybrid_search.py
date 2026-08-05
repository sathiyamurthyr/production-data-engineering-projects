"""Unit tests for the Hybrid Search pattern."""

import pytest

from src.hybrid_search import HybridSearch, HybridSearchConfig


class TestHybridSearchConfig:
    """Tests for HybridSearchConfig."""

    def test_default_config(self) -> None:
        config = HybridSearchConfig()
        assert config.pattern_name == "hybrid-search"


class TestHybridSearch:
    """Tests for HybridSearch."""

    def test_init_default_config(self) -> None:
        pattern = HybridSearch()
        assert pattern.config.pattern_name == "hybrid-search"

    def test_init_custom_config(self) -> None:
        config = HybridSearchConfig()
        pattern = HybridSearch(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = HybridSearch()
        result = pattern.execute("test_data")
        assert result == "test_data"
