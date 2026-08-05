"""Unit tests for the State Store pattern."""

import pytest

from src.state_store import StateStore, StateStoreConfig


class TestStateStoreConfig:
    """Tests for StateStoreConfig."""

    def test_default_config(self) -> None:
        config = StateStoreConfig()
        assert config.pattern_name == "state-store"


class TestStateStore:
    """Tests for StateStore."""

    def test_init_default_config(self) -> None:
        pattern = StateStore()
        assert pattern.config.pattern_name == "state-store"

    def test_init_custom_config(self) -> None:
        config = StateStoreConfig()
        pattern = StateStore(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = StateStore()
        result = pattern.execute("test_data")
        assert result == "test_data"
