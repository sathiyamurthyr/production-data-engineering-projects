"""Unit tests for the Data Access Control pattern."""

import pytest

from src.data_access_control import DataAccessControl, DataAccessControlConfig


class TestDataAccessControlConfig:
    """Tests for DataAccessControlConfig."""

    def test_default_config(self) -> None:
        config = DataAccessControlConfig()
        assert config.pattern_name == "data-access-control"


class TestDataAccessControl:
    """Tests for DataAccessControl."""

    def test_init_default_config(self) -> None:
        pattern = DataAccessControl()
        assert pattern.config.pattern_name == "data-access-control"

    def test_init_custom_config(self) -> None:
        config = DataAccessControlConfig()
        pattern = DataAccessControl(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = DataAccessControl()
        result = pattern.execute("test_data")
        assert result == "test_data"
