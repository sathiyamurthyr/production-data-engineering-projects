"""Unit tests for the Multi-Region Deployment pattern."""

import pytest

from src.multi_region import MultiRegion, MultiRegionConfig


class TestMultiRegionConfig:
    """Tests for MultiRegionConfig."""

    def test_default_config(self) -> None:
        config = MultiRegionConfig()
        assert config.pattern_name == "multi-region"


class TestMultiRegion:
    """Tests for MultiRegion."""

    def test_init_default_config(self) -> None:
        pattern = MultiRegion()
        assert pattern.config.pattern_name == "multi-region"

    def test_init_custom_config(self) -> None:
        config = MultiRegionConfig()
        pattern = MultiRegion(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = MultiRegion()
        result = pattern.execute("test_data")
        assert result == "test_data"
