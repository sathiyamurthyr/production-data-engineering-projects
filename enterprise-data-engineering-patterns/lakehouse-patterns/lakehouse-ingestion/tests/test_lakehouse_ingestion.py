"""Unit tests for the Lakehouse Ingestion pattern."""

import pytest

from src.lakehouse_ingestion import LakehouseIngestion, LakehouseIngestionConfig


class TestLakehouseIngestionConfig:
    """Tests for LakehouseIngestionConfig."""

    def test_default_config(self) -> None:
        config = LakehouseIngestionConfig()
        assert config.pattern_name == "lakehouse-ingestion"


class TestLakehouseIngestion:
    """Tests for LakehouseIngestion."""

    def test_init_default_config(self) -> None:
        pattern = LakehouseIngestion()
        assert pattern.config.pattern_name == "lakehouse-ingestion"

    def test_init_custom_config(self) -> None:
        config = LakehouseIngestionConfig()
        pattern = LakehouseIngestion(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = LakehouseIngestion()
        result = pattern.execute("test_data")
        assert result == "test_data"
