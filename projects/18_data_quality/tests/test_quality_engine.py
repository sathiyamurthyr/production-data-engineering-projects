"""
Unit tests for Quality Engine & Data Partitioning.
"""

import pytest
import pandas as pd
from src.dq_framework.quality_engine import QualityEngine
from src.rules.completeness_rules import NullCheckRule, RowCountRule
from src.rules.uniqueness_rules import PrimaryKeyUniquenessRule
from src.dq_framework.quality_rule import Severity


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "id": ["1", "2", "3", "3", None],
        "name": ["Alice", "Bob", "Charlie", "Charlie", "David"],
        "email": ["alice@test.com", "bob@test.com", "charlie@test.com", "charlie@test.com", None],
    })


def test_quality_engine_run(sample_df):
    rules = [
        NullCheckRule(columns=["id"], severity=Severity.CRITICAL),
        PrimaryKeyUniquenessRule(pk_column="id", severity=Severity.ERROR),
        RowCountRule(min_rows=1, max_rows=10, severity=Severity.INFO),
    ]
    engine = QualityEngine(rules=rules, dataset_name="test_dataset")
    report = engine.run(sample_df)

    assert report.dataset_name == "test_dataset"
    assert report.total_records == 5
    assert report.total_rules == 3
    assert report.failed_rules == 2
    assert report.status == "FAILED"


def test_quality_engine_partitioning(sample_df):
    rules = [
        NullCheckRule(columns=["id"], severity=Severity.CRITICAL),
        PrimaryKeyUniquenessRule(pk_column="id", severity=Severity.ERROR),
    ]
    engine = QualityEngine(rules=rules, dataset_name="test_dataset")
    report = engine.run(sample_df)

    clean_df, quarantine_df = engine.partition_data(sample_df, report)

    # Row 3 (dup) and Row 4 (null id & dup) should be quarantined
    assert len(quarantine_df) > 0
    assert len(clean_df) + len(quarantine_df) == len(sample_df)
