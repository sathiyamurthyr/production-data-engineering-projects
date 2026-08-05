"""Unit tests for the Metadata Catalog pattern."""

import pytest

from src.metadata_catalog import MetadataCatalog, MetadataCatalogConfig


class TestMetadataCatalogConfig:
    """Tests for MetadataCatalogConfig."""

    def test_default_config(self) -> None:
        config = MetadataCatalogConfig()
        assert config.pattern_name == "metadata-catalog"


class TestMetadataCatalog:
    """Tests for MetadataCatalog."""

    def test_init_default_config(self) -> None:
        pattern = MetadataCatalog()
        assert pattern.config.pattern_name == "metadata-catalog"

    def test_init_custom_config(self) -> None:
        config = MetadataCatalogConfig()
        pattern = MetadataCatalog(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = MetadataCatalog()
        result = pattern.execute("test_data")
        assert result == "test_data"
