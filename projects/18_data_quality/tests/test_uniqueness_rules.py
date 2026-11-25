"""
Unit tests for Uniqueness Data Quality Rules.
"""

import pytest
import pandas as pd
from src.rules.uniqueness_rules import PrimaryKeyUniquenessRule, DuplicateRowsRule
from src.dq_framework.quality_rule import Severity, Dimension


@pytest.fixture
def unique_df():
    return pd.DataFrame({
        "customer_id": ["C1", "C2", "C3", "C4"],
        "val": [10, 20, 30, 40],
    })


@pytest.fixture
def duplicate_df():
    return pd.DataFrame({
        "customer_id": ["C1", "C2", "C2", "C4"],
        "val": [10, 20, 20, 40],
    })


def test_pk_uniqueness_pass(unique_df):
    rule = PrimaryKeyUniquenessRule(pk_column="customer_id", severity=Severity.CRITICAL)
    result = rule.evaluate(unique_df)
    assert result.passed is True
    assert result.failed_count == 0
    assert result.dimension == Dimension.UNIQUENESS


def test_pk_uniqueness_fail(duplicate_df):
    rule = PrimaryKeyUniquenessRule(pk_column="customer_id", severity=Severity.CRITICAL)
    result = rule.evaluate(duplicate_df)
    assert result.passed is False
    assert result.failed_count == 2
    assert 1 in result.failed_indices
    assert 2 in result.failed_indices


def test_duplicate_rows_rule(duplicate_df):
    rule = DuplicateRowsRule(severity=Severity.WARNING)
    result = rule.evaluate(duplicate_df)
    assert result.passed is False
    assert result.failed_count == 2
