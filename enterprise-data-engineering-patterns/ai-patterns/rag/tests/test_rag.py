"""Unit tests for the RAG pattern."""

import pytest

from src.rag import Rag, RagConfig


class TestRagConfig:
    """Tests for RagConfig."""

    def test_default_config(self) -> None:
        config = RagConfig()
        assert config.pattern_name == "rag"


class TestRag:
    """Tests for Rag."""

    def test_init_default_config(self) -> None:
        pattern = Rag()
        assert pattern.config.pattern_name == "rag"

    def test_init_custom_config(self) -> None:
        config = RagConfig()
        pattern = Rag(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Rag()
        result = pattern.execute("test_data")
        assert result == "test_data"
