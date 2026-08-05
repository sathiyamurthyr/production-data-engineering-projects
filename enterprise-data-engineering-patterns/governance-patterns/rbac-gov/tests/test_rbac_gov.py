"""Unit tests for the RBAC pattern."""

import pytest

from src.rbac_gov import RbacGov, RbacGovConfig


class TestRbacGovConfig:
    """Tests for RbacGovConfig."""

    def test_default_config(self) -> None:
        config = RbacGovConfig()
        assert config.pattern_name == "rbac-gov"


class TestRbacGov:
    """Tests for RbacGov."""

    def test_init_default_config(self) -> None:
        pattern = RbacGov()
        assert pattern.config.pattern_name == "rbac-gov"

    def test_init_custom_config(self) -> None:
        config = RbacGovConfig()
        pattern = RbacGov(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = RbacGov()
        result = pattern.execute("test_data")
        assert result == "test_data"
