"""Unit tests for the Least Privilege pattern."""

import pytest

from src.least_privilege_gov import LeastPrivilegeGov, LeastPrivilegeGovConfig


class TestLeastPrivilegeGovConfig:
    """Tests for LeastPrivilegeGovConfig."""

    def test_default_config(self) -> None:
        config = LeastPrivilegeGovConfig()
        assert config.pattern_name == "least-privilege-gov"


class TestLeastPrivilegeGov:
    """Tests for LeastPrivilegeGov."""

    def test_init_default_config(self) -> None:
        pattern = LeastPrivilegeGov()
        assert pattern.config.pattern_name == "least-privilege-gov"

    def test_init_custom_config(self) -> None:
        config = LeastPrivilegeGovConfig()
        pattern = LeastPrivilegeGov(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = LeastPrivilegeGov()
        result = pattern.execute("test_data")
        assert result == "test_data"
