"""Unit tests for the CI/CD Pipeline pattern."""

import pytest

from src.ci_cd import CiCd, CiCdConfig


class TestCiCdConfig:
    """Tests for CiCdConfig."""

    def test_default_config(self) -> None:
        config = CiCdConfig()
        assert config.pattern_name == "ci-cd"


class TestCiCd:
    """Tests for CiCd."""

    def test_init_default_config(self) -> None:
        pattern = CiCd()
        assert pattern.config.pattern_name == "ci-cd"

    def test_init_custom_config(self) -> None:
        config = CiCdConfig()
        pattern = CiCd(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = CiCd()
        result = pattern.execute("test_data")
        assert result == "test_data"
