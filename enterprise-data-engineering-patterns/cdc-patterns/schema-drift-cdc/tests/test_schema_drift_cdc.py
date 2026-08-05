"""Unit tests for the Schema Drift CDC pattern."""

import pytest

from src.schema_drift_cdc import SchemaDriftCdc, SchemaDriftCdcConfig


class TestSchemaDriftCdcConfig:
    """Tests for SchemaDriftCdcConfig."""

    def test_default_config(self) -> None:
        config = SchemaDriftCdcConfig()
        assert config.pattern_name == "schema-drift-cdc"


class TestSchemaDriftCdc:
    """Tests for SchemaDriftCdc."""

    def test_init_default_config(self) -> None:
        pattern = SchemaDriftCdc()
        assert pattern.config.pattern_name == "schema-drift-cdc"

    def test_init_custom_config(self) -> None:
        config = SchemaDriftCdcConfig()
        pattern = SchemaDriftCdc(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = SchemaDriftCdc()
        result = pattern.execute("test_data")
        assert result == "test_data"
