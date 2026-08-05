"""Unit tests for the Conversation Memory pattern."""

import pytest

from src.conversation_memory import ConversationMemory, ConversationMemoryConfig


class TestConversationMemoryConfig:
    """Tests for ConversationMemoryConfig."""

    def test_default_config(self) -> None:
        config = ConversationMemoryConfig()
        assert config.pattern_name == "conversation-memory"


class TestConversationMemory:
    """Tests for ConversationMemory."""

    def test_init_default_config(self) -> None:
        pattern = ConversationMemory()
        assert pattern.config.pattern_name == "conversation-memory"

    def test_init_custom_config(self) -> None:
        config = ConversationMemoryConfig()
        pattern = ConversationMemory(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ConversationMemory()
        result = pattern.execute("test_data")
        assert result == "test_data"
