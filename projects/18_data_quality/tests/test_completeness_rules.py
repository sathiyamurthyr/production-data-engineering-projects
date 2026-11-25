"""
Unit tests for Completeness Data Quality Rules.
"""

import pytest
import pandas as pd
from src.rules.completeness_rules import NullCheckRule, RowCountRule, RequiredColumnsRule
from src.dq_framework.quality_rule import Severity, Dimension


@pytest.fixture
def clean_df():
    return pd.DataFrame({
        "customer_id": ["CUST001", "CUST002", "CUST003"],
        "email": ["a@test.com", "b@test.com", "c@test.com"],
        "age": [25, 30, 35],
    })


@pytest.fixture
def dirty_df():
    return pd.DataFrame({
        "customer_id": ["CUST001", None, "CUST003"],
        "email": ["a@test.com", "b@test.com", None],
        "age": [25, 30, 35],
    })


def test_null_check_rule_clean(clean_df):
    rule = NullCheckRule(columns=["customer_id", "email"], severity=Severity.ERROR)
    result = rule.evaluate(clean_df)
    
    assert result.passed is True
    assert result.failed_count == 0
    assert result.passed_count == 3
    assert result.dimension == Dimension.COMPLETENESS


def test_null_check_rule_dirty(dirty_df):
    rule = NullCheckRule(columns=["customer_id", "email"], severity=Severity.ERROR)
    result = rule.evaluate(dirty_df)
    
    assert result.passed is False
    assert result.failed_count == 2
    assert 1 in result.failed_indices
    assert 2 in result.failed_indices


def test_row_count_rule_pass(clean_df):
    rule = RowCountRule(min_rows=1, max_rows=10, severity=Severity.CRITICAL)
    result = rule.evaluate(clean_df)
    assert result.passed is True
    assert result.passed_count == 3


def test_row_count_rule_fail_below_min(clean_df):
    rule = RowCountRule(min_rows=10, max_rows=100, severity=Severity.CRITICAL)
    result = rule.evaluate(clean_df)
    assert result.passed is False
    assert result.failed_count == 3


def test_required_columns_rule_pass(clean_df):
    rule = RequiredColumnsRule(expected_columns=["customer_id", "email", "age"])
    result = rule.evaluate(clean_df)
    assert result.passed is True


def test_required_columns_rule_fail(clean_df):
    rule = RequiredColumnsRule(expected_columns=["customer_id", "phone_number"])
    result = rule.evaluate(clean_df)
    assert result.passed is False
    assert "phone_number" in result.details["missing_columns"]
