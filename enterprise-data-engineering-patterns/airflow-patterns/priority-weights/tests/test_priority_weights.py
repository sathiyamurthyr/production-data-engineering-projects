"""Unit tests for the Priority Weights pattern."""

import pytest

from src.priority_weights import PriorityWeights, PriorityWeightsConfig


class TestPriorityWeightsConfig:
    """Tests for PriorityWeightsConfig."""

    def test_default_config(self) -> None:
        config = PriorityWeightsConfig()
        assert config.pattern_name == "priority-weights"


class TestPriorityWeights:
    """Tests for PriorityWeights."""

    def test_init_default_config(self) -> None:
        pattern = PriorityWeights()
        assert pattern.config.pattern_name == "priority-weights"

    def test_init_custom_config(self) -> None:
        config = PriorityWeightsConfig()
        pattern = PriorityWeights(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = PriorityWeights()
        result = pattern.execute("test_data")
        assert result == "test_data"
