"""Unit tests for the CDC with Schema Registry pattern."""

import pytest

from src.cdc_schema_registry import CdcSchemaRegistry, CdcSchemaRegistryConfig


class TestCdcSchemaRegistryConfig:
    """Tests for CdcSchemaRegistryConfig."""

    def test_default_config(self) -> None:
        config = CdcSchemaRegistryConfig()
        assert config.pattern_name == "cdc-schema-registry"


class TestCdcSchemaRegistry:
    """Tests for CdcSchemaRegistry."""

    def test_init_default_config(self) -> None:
        pattern = CdcSchemaRegistry()
        assert pattern.config.pattern_name == "cdc-schema-registry"

    def test_init_custom_config(self) -> None:
        config = CdcSchemaRegistryConfig()
        pattern = CdcSchemaRegistry(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = CdcSchemaRegistry()
        result = pattern.execute("test_data")
        assert result == "test_data"
