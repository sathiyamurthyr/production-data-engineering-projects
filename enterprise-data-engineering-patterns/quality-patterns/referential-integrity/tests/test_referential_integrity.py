"""Unit tests for the Referential Integrity pattern."""

import pytest

from src.referential_integrity import ReferentialIntegrity, ReferentialIntegrityConfig


class TestReferentialIntegrityConfig:
    """Tests for ReferentialIntegrityConfig."""

    def test_default_config(self) -> None:
        config = ReferentialIntegrityConfig()
        assert config.pattern_name == "referential-integrity"


class TestReferentialIntegrity:
    """Tests for ReferentialIntegrity."""

    def test_init_default_config(self) -> None:
        pattern = ReferentialIntegrity()
        assert pattern.config.pattern_name == "referential-integrity"

    def test_init_custom_config(self) -> None:
        config = ReferentialIntegrityConfig()
        pattern = ReferentialIntegrity(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ReferentialIntegrity()
        result = pattern.execute("test_data")
        assert result == "test_data"
