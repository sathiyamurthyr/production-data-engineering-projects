"""Unit tests for the Embedding Generation pattern."""

import pytest

from src.embedding_generation import EmbeddingGeneration, EmbeddingGenerationConfig


class TestEmbeddingGenerationConfig:
    """Tests for EmbeddingGenerationConfig."""

    def test_default_config(self) -> None:
        config = EmbeddingGenerationConfig()
        assert config.pattern_name == "embedding-generation"


class TestEmbeddingGeneration:
    """Tests for EmbeddingGeneration."""

    def test_init_default_config(self) -> None:
        pattern = EmbeddingGeneration()
        assert pattern.config.pattern_name == "embedding-generation"

    def test_init_custom_config(self) -> None:
        config = EmbeddingGenerationConfig()
        pattern = EmbeddingGeneration(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = EmbeddingGeneration()
        result = pattern.execute("test_data")
        assert result == "test_data"
