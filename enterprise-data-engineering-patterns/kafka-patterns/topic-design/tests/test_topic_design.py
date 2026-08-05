"""Unit tests for the Topic Design pattern."""

import pytest

from src.topic_design import TopicDesign, TopicDesignConfig


class TestTopicDesignConfig:
    """Tests for TopicDesignConfig."""

    def test_default_config(self) -> None:
        config = TopicDesignConfig()
        assert config.pattern_name == "topic-design"


class TestTopicDesign:
    """Tests for TopicDesign."""

    def test_init_default_config(self) -> None:
        pattern = TopicDesign()
        assert pattern.config.pattern_name == "topic-design"

    def test_init_custom_config(self) -> None:
        config = TopicDesignConfig()
        pattern = TopicDesign(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = TopicDesign()
        result = pattern.execute("test_data")
        assert result == "test_data"
