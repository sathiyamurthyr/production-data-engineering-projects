"""Unit tests for the Document Ingestion pattern."""

import pytest

from src.document_ingestion import DocumentIngestion, DocumentIngestionConfig


class TestDocumentIngestionConfig:
    """Tests for DocumentIngestionConfig."""

    def test_default_config(self) -> None:
        config = DocumentIngestionConfig()
        assert config.pattern_name == "document-ingestion"


class TestDocumentIngestion:
    """Tests for DocumentIngestion."""

    def test_init_default_config(self) -> None:
        pattern = DocumentIngestion()
        assert pattern.config.pattern_name == "document-ingestion"

    def test_init_custom_config(self) -> None:
        config = DocumentIngestionConfig()
        pattern = DocumentIngestion(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DocumentIngestion()
        result = pattern.execute("test_data")
        assert result == "test_data"
