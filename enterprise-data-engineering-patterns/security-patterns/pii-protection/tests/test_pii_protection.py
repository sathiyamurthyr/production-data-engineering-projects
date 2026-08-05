"""Unit tests for the PII Protection pattern."""

import pytest

from src.pii_protection import PiiProtection, PiiProtectionConfig


class TestPiiProtectionConfig:
    """Tests for PiiProtectionConfig."""

    def test_default_config(self) -> None:
        config = PiiProtectionConfig()
        assert config.pattern_name == "pii-protection"


class TestPiiProtection:
    """Tests for PiiProtection."""

    def test_init_default_config(self) -> None:
        pattern = PiiProtection()
        assert pattern.config.pattern_name == "pii-protection"

    def test_init_custom_config(self) -> None:
        config = PiiProtectionConfig()
        pattern = PiiProtection(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = PiiProtection()
        result = pattern.execute("test_data")
        assert result == "test_data"
