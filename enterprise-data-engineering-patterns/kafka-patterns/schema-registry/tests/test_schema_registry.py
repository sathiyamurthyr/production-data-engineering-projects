"""Unit tests for the Schema Registry Concepts pattern."""

import pytest

from src.schema_registry import SchemaRegistry, SchemaRegistryConfig


class TestSchemaRegistryConfig:
    """Tests for SchemaRegistryConfig."""

    def test_default_config(self) -> None:
        config = SchemaRegistryConfig()
        assert config.pattern_name == "schema-registry"


class TestSchemaRegistry:
    """Tests for SchemaRegistry."""

    def test_init_default_config(self) -> None:
        pattern = SchemaRegistry()
        assert pattern.config.pattern_name == "schema-registry"

    def test_init_custom_config(self) -> None:
        config = SchemaRegistryConfig()
        pattern = SchemaRegistry(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = SchemaRegistry()
        result = pattern.execute("test_data")
        assert result == "test_data"
