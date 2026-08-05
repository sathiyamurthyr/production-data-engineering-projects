"""Unit tests for the Surrogate Keys pattern."""

import pytest

from src.surrogate_keys import SurrogateKeys, SurrogateKeysConfig


class TestSurrogateKeysConfig:
    """Tests for SurrogateKeysConfig."""

    def test_default_config(self) -> None:
        config = SurrogateKeysConfig()
        assert config.pattern_name == "surrogate-keys"


class TestSurrogateKeys:
    """Tests for SurrogateKeys."""

    def test_init_default_config(self) -> None:
        pattern = SurrogateKeys()
        assert pattern.config.pattern_name == "surrogate-keys"

    def test_init_custom_config(self) -> None:
        config = SurrogateKeysConfig()
        pattern = SurrogateKeys(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = SurrogateKeys()
        result = pattern.execute("test_data")
        assert result == "test_data"
