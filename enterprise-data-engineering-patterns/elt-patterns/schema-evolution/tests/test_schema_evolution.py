"""Unit tests for the Schema Evolution pattern."""

import pytest

from src.schema_evolution import SchemaEvolution, SchemaEvolutionConfig


class TestSchemaEvolutionConfig:
    """Tests for SchemaEvolutionConfig."""

    def test_default_config(self) -> None:
        config = SchemaEvolutionConfig()
        assert config.pattern_name == "schema-evolution"


class TestSchemaEvolution:
    """Tests for SchemaEvolution."""

    def test_init_default_config(self) -> None:
        pattern = SchemaEvolution()
        assert pattern.config.pattern_name == "schema-evolution"

    def test_init_custom_config(self) -> None:
        config = SchemaEvolutionConfig()
        pattern = SchemaEvolution(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = SchemaEvolution()
        result = pattern.execute("test_data")
        assert result == "test_data"
