"""Unit tests for the Dead Letter Queue pattern."""

import pytest

from src.dead_letter_queue import DeadLetterQueue, DeadLetterQueueConfig


class TestDeadLetterQueueConfig:
    """Tests for DeadLetterQueueConfig."""

    def test_default_config(self) -> None:
        config = DeadLetterQueueConfig()
        assert config.pattern_name == "dead-letter-queue"


class TestDeadLetterQueue:
    """Tests for DeadLetterQueue."""

    def test_init_default_config(self) -> None:
        pattern = DeadLetterQueue()
        assert pattern.config.pattern_name == "dead-letter-queue"

    def test_init_custom_config(self) -> None:
        config = DeadLetterQueueConfig()
        pattern = DeadLetterQueue(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DeadLetterQueue()
        result = pattern.execute("test_data")
        assert result == "test_data"
