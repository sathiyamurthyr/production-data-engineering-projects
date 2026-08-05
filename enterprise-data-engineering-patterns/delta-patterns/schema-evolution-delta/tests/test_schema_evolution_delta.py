"""Unit tests for the Schema Evolution pattern."""

import pytest

from src.schema_evolution_delta import SchemaEvolutionDelta, SchemaEvolutionDeltaConfig


class TestSchemaEvolutionDeltaConfig:
    """Tests for SchemaEvolutionDeltaConfig."""

    def test_default_config(self) -> None:
        config = SchemaEvolutionDeltaConfig()
        assert config.pattern_name == "schema-evolution-delta"


class TestSchemaEvolutionDelta:
    """Tests for SchemaEvolutionDelta."""

    def test_init_default_config(self) -> None:
        pattern = SchemaEvolutionDelta()
        assert pattern.config.pattern_name == "schema-evolution-delta"

    def test_init_custom_config(self) -> None:
        config = SchemaEvolutionDeltaConfig()
        pattern = SchemaEvolutionDelta(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = SchemaEvolutionDelta()
        result = pattern.execute("test_data")
        assert result == "test_data"
