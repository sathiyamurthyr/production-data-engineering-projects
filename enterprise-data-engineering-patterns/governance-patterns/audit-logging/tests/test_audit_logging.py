"""Unit tests for the Audit Logging pattern."""

import pytest

from src.audit_logging import AuditLogging, AuditLoggingConfig


class TestAuditLoggingConfig:
    """Tests for AuditLoggingConfig."""

    def test_default_config(self) -> None:
        config = AuditLoggingConfig()
        assert config.pattern_name == "audit-logging"


class TestAuditLogging:
    """Tests for AuditLogging."""

    def test_init_default_config(self) -> None:
        pattern = AuditLogging()
        assert pattern.config.pattern_name == "audit-logging"

    def test_init_custom_config(self) -> None:
        config = AuditLoggingConfig()
        pattern = AuditLogging(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = AuditLogging()
        result = pattern.execute("test_data")
        assert result == "test_data"
