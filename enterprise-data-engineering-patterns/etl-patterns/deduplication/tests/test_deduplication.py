"""Unit tests for the Deduplication pattern."""

import pytest

from src.deduplication import Deduplication, DeduplicationConfig


class TestDeduplicationConfig:
    """Tests for DeduplicationConfig."""

    def test_default_config(self) -> None:
        config = DeduplicationConfig()
        assert config.pattern_name == "deduplication"


class TestDeduplication:
    """Tests for Deduplication."""

    def test_init_default_config(self) -> None:
        pattern = Deduplication()
        assert pattern.config.pattern_name == "deduplication"

    def test_init_custom_config(self) -> None:
        config = DeduplicationConfig()
        pattern = Deduplication(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = Deduplication()
        result = pattern.execute("test_data")
        assert result == "test_data"
