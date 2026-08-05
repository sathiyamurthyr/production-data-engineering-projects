"""Unit tests for the Hub-and-Spoke pattern."""

import pytest

from src.hub_and_spoke import HubAndSpoke, HubAndSpokeConfig


class TestHubAndSpokeConfig:
    """Tests for HubAndSpokeConfig."""

    def test_default_config(self) -> None:
        config = HubAndSpokeConfig()
        assert config.pattern_name == "hub-and-spoke"


class TestHubAndSpoke:
    """Tests for HubAndSpoke."""

    def test_init_default_config(self) -> None:
        pattern = HubAndSpoke()
        assert pattern.config.pattern_name == "hub-and-spoke"

    def test_init_custom_config(self) -> None:
        config = HubAndSpokeConfig()
        pattern = HubAndSpoke(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = HubAndSpoke()
        result = pattern.execute("test_data")
        assert result == "test_data"
