"""Unit tests for the Webhook Ingestion pattern."""

import pytest

from src.webhook_ingestion import WebhookIngestion, WebhookIngestionConfig


class TestWebhookIngestionConfig:
    """Tests for WebhookIngestionConfig."""

    def test_default_config(self) -> None:
        config = WebhookIngestionConfig()
        assert config.pattern_name == "webhook-ingestion"


class TestWebhookIngestion:
    """Tests for WebhookIngestion."""

    def test_init_default_config(self) -> None:
        pattern = WebhookIngestion()
        assert pattern.config.pattern_name == "webhook-ingestion"

    def test_init_custom_config(self) -> None:
        config = WebhookIngestionConfig()
        pattern = WebhookIngestion(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = WebhookIngestion()
        result = pattern.execute("test_data")
        assert result == "test_data"
