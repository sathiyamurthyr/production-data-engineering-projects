"""Unit tests for the RBAC pattern."""

import pytest

from src.rbac_sec import RbacSec, RbacSecConfig


class TestRbacSecConfig:
    """Tests for RbacSecConfig."""

    def test_default_config(self) -> None:
        config = RbacSecConfig()
        assert config.pattern_name == "rbac-sec"


class TestRbacSec:
    """Tests for RbacSec."""

    def test_init_default_config(self) -> None:
        pattern = RbacSec()
        assert pattern.config.pattern_name == "rbac-sec"

    def test_init_custom_config(self) -> None:
        config = RbacSecConfig()
        pattern = RbacSec(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = RbacSec()
        result = pattern.execute("test_data")
        assert result == "test_data"
