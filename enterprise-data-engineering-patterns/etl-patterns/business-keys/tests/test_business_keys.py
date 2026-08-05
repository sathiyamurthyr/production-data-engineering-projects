"""Unit tests for the Business Keys pattern."""

import pytest

from src.business_keys import BusinessKeys, BusinessKeysConfig


class TestBusinessKeysConfig:
    """Tests for BusinessKeysConfig."""

    def test_default_config(self) -> None:
        config = BusinessKeysConfig()
        assert config.pattern_name == "business-keys"


class TestBusinessKeys:
    """Tests for BusinessKeys."""

    def test_init_default_config(self) -> None:
        pattern = BusinessKeys()
        assert pattern.config.pattern_name == "business-keys"

    def test_init_custom_config(self) -> None:
        config = BusinessKeysConfig()
        pattern = BusinessKeys(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = BusinessKeys()
        result = pattern.execute("test_data")
        assert result == "test_data"
