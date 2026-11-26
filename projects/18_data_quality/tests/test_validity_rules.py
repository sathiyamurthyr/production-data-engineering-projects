"""
Unit tests for Validity Data Quality Rules.
"""

import pytest
import pandas as pd
from src.rules.validity_rules import (
    EmailFormatRule,
    NumericRangeRule,
    ValueSetRule,
    RegexMatchRule,
    DateRangeRule,
)
from src.dq_framework.quality_rule import Severity, Dimension


def test_email_format_rule():
    df = pd.DataFrame({
        "email": ["user@example.com", "valid.email@company.co.uk", "bad-email-str", "user@domain", None]
    })
    rule = EmailFormatRule(column="email", severity=Severity.WARNING)
    result = rule.evaluate(df)
    
    assert result.passed is False
    assert result.failed_count == 2
    assert 2 in result.failed_indices  # bad-email-str
    assert 3 in result.failed_indices  # user@domain


def test_numeric_range_rule():
    df = pd.DataFrame({"age": [25, 17, 45, 130, -5]})
    rule = NumericRangeRule(column="age", min_val=18, max_val=120)
    result = rule.evaluate(df)

    assert result.passed is False
    assert result.failed_count == 3
    assert set(result.failed_indices) == {1, 3, 4}


def test_value_set_rule():
    df = pd.DataFrame({"status": ["ACTIVE", "INACTIVE", "INVALID", "SUSPENDED"]})
    rule = ValueSetRule(column="status", allowed_values=["ACTIVE", "INACTIVE", "SUSPENDED"])
    result = rule.evaluate(df)

    assert result.passed is False
    assert result.failed_count == 1
    assert result.failed_indices == [2]


def test_regex_match_rule():
    df = pd.DataFrame({"phone": ["123-456-7890", "987-654-3210", "12345", "abc-def-ghij"]})
    rule = RegexMatchRule(column="phone", pattern=r"^\d{3}-\d{3}-\d{4}$")
    result = rule.evaluate(df)

    assert result.passed is False
    assert result.failed_count == 2
    assert set(result.failed_indices) == {2, 3}


def test_date_range_rule():
    df = pd.DataFrame({"signup_date": ["2023-01-01", "2023-06-15", "1995-05-10", "2099-12-31"]})
    rule = DateRangeRule(column="signup_date", min_date="2000-01-01", max_date="2025-01-01")
    result = rule.evaluate(df)

    assert result.passed is False
    assert result.failed_count == 2
    assert set(result.failed_indices) == {2, 3}
