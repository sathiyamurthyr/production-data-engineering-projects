"""Unit tests for the Zero Trust Concepts pattern."""

import pytest

from src.zero_trust import ZeroTrust, ZeroTrustConfig


class TestZeroTrustConfig:
    """Tests for ZeroTrustConfig."""

    def test_default_config(self) -> None:
        config = ZeroTrustConfig()
        assert config.pattern_name == "zero-trust"


class TestZeroTrust:
    """Tests for ZeroTrust."""

    def test_init_default_config(self) -> None:
        pattern = ZeroTrust()
        assert pattern.config.pattern_name == "zero-trust"

    def test_init_custom_config(self) -> None:
        config = ZeroTrustConfig()
        pattern = ZeroTrust(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ZeroTrust()
        result = pattern.execute("test_data")
        assert result == "test_data"
