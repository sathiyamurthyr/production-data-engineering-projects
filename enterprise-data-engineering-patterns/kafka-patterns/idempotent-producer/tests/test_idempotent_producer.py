"""Unit tests for the Idempotent Producer Concepts pattern."""

import pytest

from src.idempotent_producer import IdempotentProducer, IdempotentProducerConfig


class TestIdempotentProducerConfig:
    """Tests for IdempotentProducerConfig."""

    def test_default_config(self) -> None:
        config = IdempotentProducerConfig()
        assert config.pattern_name == "idempotent-producer"


class TestIdempotentProducer:
    """Tests for IdempotentProducer."""

    def test_init_default_config(self) -> None:
        pattern = IdempotentProducer()
        assert pattern.config.pattern_name == "idempotent-producer"

    def test_init_custom_config(self) -> None:
        config = IdempotentProducerConfig()
        pattern = IdempotentProducer(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = IdempotentProducer()
        result = pattern.execute("test_data")
        assert result == "test_data"
