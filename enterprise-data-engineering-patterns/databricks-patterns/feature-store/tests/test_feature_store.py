"""Unit tests for the Feature Store pattern."""

import pytest

from src.feature_store import FeatureStore, FeatureStoreConfig


class TestFeatureStoreConfig:
    """Tests for FeatureStoreConfig."""

    def test_default_config(self) -> None:
        config = FeatureStoreConfig()
        assert config.pattern_name == "feature-store"


class TestFeatureStore:
    """Tests for FeatureStore."""

    def test_init_default_config(self) -> None:
        pattern = FeatureStore()
        assert pattern.config.pattern_name == "feature-store"

    def test_init_custom_config(self) -> None:
        config = FeatureStoreConfig()
        pattern = FeatureStore(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = FeatureStore()
        result = pattern.execute("test_data")
        assert result == "test_data"
