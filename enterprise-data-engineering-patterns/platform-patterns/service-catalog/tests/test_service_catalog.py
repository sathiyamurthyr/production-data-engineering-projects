"""Unit tests for the Service Catalog pattern."""

import pytest

from src.service_catalog import ServiceCatalog, ServiceCatalogConfig


class TestServiceCatalogConfig:
    """Tests for ServiceCatalogConfig."""

    def test_default_config(self) -> None:
        config = ServiceCatalogConfig()
        assert config.pattern_name == "service-catalog"


class TestServiceCatalog:
    """Tests for ServiceCatalog."""

    def test_init_default_config(self) -> None:
        pattern = ServiceCatalog()
        assert pattern.config.pattern_name == "service-catalog"

    def test_init_custom_config(self) -> None:
        config = ServiceCatalogConfig()
        pattern = ServiceCatalog(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ServiceCatalog()
        result = pattern.execute("test_data")
        assert result == "test_data"
