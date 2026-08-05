"""Unit tests for the Similarity Search pattern."""

import pytest

from src.similarity_search import SimilaritySearch, SimilaritySearchConfig


class TestSimilaritySearchConfig:
    """Tests for SimilaritySearchConfig."""

    def test_default_config(self) -> None:
        config = SimilaritySearchConfig()
        assert config.pattern_name == "similarity-search"


class TestSimilaritySearch:
    """Tests for SimilaritySearch."""

    def test_init_default_config(self) -> None:
        pattern = SimilaritySearch()
        assert pattern.config.pattern_name == "similarity-search"

    def test_init_custom_config(self) -> None:
        config = SimilaritySearchConfig()
        pattern = SimilaritySearch(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = SimilaritySearch()
        result = pattern.execute("test_data")
        assert result == "test_data"
