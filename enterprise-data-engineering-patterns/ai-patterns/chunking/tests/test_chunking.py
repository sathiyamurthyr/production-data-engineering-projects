"""Unit tests for the Chunking pattern."""

import pytest

from src.chunking import Chunking, ChunkingConfig


class TestChunkingConfig:
    """Tests for ChunkingConfig."""

    def test_default_config(self) -> None:
        config = ChunkingConfig()
        assert config.pattern_name == "chunking"


class TestChunking:
    """Tests for Chunking."""

    def test_init_default_config(self) -> None:
        pattern = Chunking()
        assert pattern.config.pattern_name == "chunking"

    def test_init_custom_config(self) -> None:
        config = ChunkingConfig()
        pattern = Chunking(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Chunking()
        result = pattern.execute("test_data")
        assert result == "test_data"
