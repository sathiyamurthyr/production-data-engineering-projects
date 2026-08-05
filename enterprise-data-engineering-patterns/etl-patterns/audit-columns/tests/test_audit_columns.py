"""Unit tests for the Audit Columns pattern."""

import pytest

from src.audit_columns import AuditColumns, AuditColumnsConfig


class TestAuditColumnsConfig:
    """Tests for AuditColumnsConfig."""

    def test_default_config(self) -> None:
        config = AuditColumnsConfig()
        assert config.pattern_name == "audit-columns"


class TestAuditColumns:
    """Tests for AuditColumns."""

    def test_init_default_config(self) -> None:
        pattern = AuditColumns()
        assert pattern.config.pattern_name == "audit-columns"

    def test_init_custom_config(self) -> None:
        config = AuditColumnsConfig()
        pattern = AuditColumns(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = AuditColumns()
        result = pattern.execute("test_data")
        assert result == "test_data"
