"""Unit tests for the Hybrid Cloud pattern."""

import pytest

from src.hybrid_cloud import HybridCloud, HybridCloudConfig


class TestHybridCloudConfig:
    """Tests for HybridCloudConfig."""

    def test_default_config(self) -> None:
        config = HybridCloudConfig()
        assert config.pattern_name == "hybrid-cloud"


class TestHybridCloud:
    """Tests for HybridCloud."""

    def test_init_default_config(self) -> None:
        pattern = HybridCloud()
        assert pattern.config.pattern_name == "hybrid-cloud"

    def test_init_custom_config(self) -> None:
        config = HybridCloudConfig()
        pattern = HybridCloud(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = HybridCloud()
        result = pattern.execute("test_data")
        assert result == "test_data"
