"""Unit tests for the Consumer Groups pattern."""

import pytest

from src.consumer_groups import ConsumerGroups, ConsumerGroupsConfig


class TestConsumerGroupsConfig:
    """Tests for ConsumerGroupsConfig."""

    def test_default_config(self) -> None:
        config = ConsumerGroupsConfig()
        assert config.pattern_name == "consumer-groups"


class TestConsumerGroups:
    """Tests for ConsumerGroups."""

    def test_init_default_config(self) -> None:
        pattern = ConsumerGroups()
        assert pattern.config.pattern_name == "consumer-groups"

    def test_init_custom_config(self) -> None:
        config = ConsumerGroupsConfig()
        pattern = ConsumerGroups(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ConsumerGroups()
        result = pattern.execute("test_data")
        assert result == "test_data"
