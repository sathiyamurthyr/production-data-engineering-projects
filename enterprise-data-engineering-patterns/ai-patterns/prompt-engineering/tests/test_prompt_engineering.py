"""Unit tests for the Prompt Engineering pattern."""

import pytest

from src.prompt_engineering import PromptEngineering, PromptEngineeringConfig


class TestPromptEngineeringConfig:
    """Tests for PromptEngineeringConfig."""

    def test_default_config(self) -> None:
        config = PromptEngineeringConfig()
        assert config.pattern_name == "prompt-engineering"


class TestPromptEngineering:
    """Tests for PromptEngineering."""

    def test_init_default_config(self) -> None:
        pattern = PromptEngineering()
        assert pattern.config.pattern_name == "prompt-engineering"

    def test_init_custom_config(self) -> None:
        config = PromptEngineeringConfig()
        pattern = PromptEngineering(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = PromptEngineering()
        result = pattern.execute("test_data")
        assert result == "test_data"
