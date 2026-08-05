"""Unit tests for the Embeddings pattern."""

import pytest

from src.embeddings import Embeddings, EmbeddingsConfig


class TestEmbeddingsConfig:
    """Tests for EmbeddingsConfig."""

    def test_default_config(self) -> None:
        config = EmbeddingsConfig()
        assert config.pattern_name == "embeddings"


class TestEmbeddings:
    """Tests for Embeddings."""

    def test_init_default_config(self) -> None:
        pattern = Embeddings()
        assert pattern.config.pattern_name == "embeddings"

    def test_init_custom_config(self) -> None:
        config = EmbeddingsConfig()
        pattern = Embeddings(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Embeddings()
        result = pattern.execute("test_data")
        assert result == "test_data"
