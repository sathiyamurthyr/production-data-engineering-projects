"""Unit tests for the Feature Flag pattern."""

import pytest

from src.feature_flag import FeatureFlag, FeatureFlagConfig


class TestFeatureFlagConfig:
    """Tests for FeatureFlagConfig."""

    def test_default_config(self) -> None:
        config = FeatureFlagConfig()
        assert config.pattern_name == "feature-flag"


class TestFeatureFlag:
    """Tests for FeatureFlag."""

    def test_init_default_config(self) -> None:
        pattern = FeatureFlag()
        assert pattern.config.pattern_name == "feature-flag"

    def test_init_custom_config(self) -> None:
        config = FeatureFlagConfig()
        pattern = FeatureFlag(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = FeatureFlag()
        result = pattern.execute("test_data")
        assert result == "test_data"
