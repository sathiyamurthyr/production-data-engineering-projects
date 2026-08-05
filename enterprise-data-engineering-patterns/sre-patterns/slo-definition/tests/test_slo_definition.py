"""Unit tests for the SLO Definition pattern."""

import pytest

from src.slo_definition import SloDefinition, SloDefinitionConfig


class TestSloDefinitionConfig:
    """Tests for SloDefinitionConfig."""

    def test_default_config(self) -> None:
        config = SloDefinitionConfig()
        assert config.pattern_name == "slo-definition"


class TestSloDefinition:
    """Tests for SloDefinition."""

    def test_init_default_config(self) -> None:
        pattern = SloDefinition()
        assert pattern.config.pattern_name == "slo-definition"

    def test_init_custom_config(self) -> None:
        config = SloDefinitionConfig()
        pattern = SloDefinition(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = SloDefinition()
        result = pattern.execute("test_data")
        assert result == "test_data"
