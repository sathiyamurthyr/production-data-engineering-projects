"""Unit tests for the Compliance Reporting pattern."""

import pytest

from src.compliance_reporting import ComplianceReporting, ComplianceReportingConfig


class TestComplianceReportingConfig:
    """Tests for ComplianceReportingConfig."""

    def test_default_config(self) -> None:
        config = ComplianceReportingConfig()
        assert config.pattern_name == "compliance-reporting"


class TestComplianceReporting:
    """Tests for ComplianceReporting."""

    def test_init_default_config(self) -> None:
        pattern = ComplianceReporting()
        assert pattern.config.pattern_name == "compliance-reporting"

    def test_init_custom_config(self) -> None:
        config = ComplianceReportingConfig()
        pattern = ComplianceReporting(config)
        assert pattern.config == config

    def test_execute(self) -> None:
        pattern = ComplianceReporting()
        result = pattern.execute("test_data")
        assert result == "test_data"
