"""Unit tests for the Schema Registry pattern."""

import pytest

from src.schema_registry_m import SchemaRegistryM, SchemaRegistryMConfig


class TestSchemaRegistryMConfig:
    """Tests for SchemaRegistryMConfig."""

    def test_default_config(self) -> None:
        config = SchemaRegistryMConfig()
        assert config.pattern_name == "schema-registry-m"


class TestSchemaRegistryM:
    """Tests for SchemaRegistryM."""

    def test_init_default_config(self) -> None:
        pattern = SchemaRegistryM()
        assert pattern.config.pattern_name == "schema-registry-m"

    def test_init_custom_config(self) -> None:
        config = SchemaRegistryMConfig()
        pattern = SchemaRegistryM(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = SchemaRegistryM()
        result = pattern.execute("test_data")
        assert result == "test_data"
