"""Unit tests for the Zero Copy Cloning pattern."""

import pytest

from src.zero_copy_clone import ZeroCopyClone, ZeroCopyCloneConfig


class TestZeroCopyCloneConfig:
    """Tests for ZeroCopyCloneConfig."""

    def test_default_config(self) -> None:
        config = ZeroCopyCloneConfig()
        assert config.pattern_name == "zero-copy-clone"


class TestZeroCopyClone:
    """Tests for ZeroCopyClone."""

    def test_init_default_config(self) -> None:
        pattern = ZeroCopyClone()
        assert pattern.config.pattern_name == "zero-copy-clone"

    def test_init_custom_config(self) -> None:
        config = ZeroCopyCloneConfig()
        pattern = ZeroCopyClone(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ZeroCopyClone()
        result = pattern.execute("test_data")
        assert result == "test_data"
