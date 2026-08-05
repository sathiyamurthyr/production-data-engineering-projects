"""Unit tests for the Cloud Migration pattern."""

import pytest

from src.cloud_migration import CloudMigration, CloudMigrationConfig


class TestCloudMigrationConfig:
    """Tests for CloudMigrationConfig."""

    def test_default_config(self) -> None:
        config = CloudMigrationConfig()
        assert config.pattern_name == "cloud-migration"


class TestCloudMigration:
    """Tests for CloudMigration."""

    def test_init_default_config(self) -> None:
        pattern = CloudMigration()
        assert pattern.config.pattern_name == "cloud-migration"

    def test_init_custom_config(self) -> None:
        config = CloudMigrationConfig()
        pattern = CloudMigration(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = CloudMigration()
        result = pattern.execute("test_data")
        assert result == "test_data"
