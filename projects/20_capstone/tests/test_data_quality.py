import pytest
import pandas as pd
from src.silver.data_quality_checks import DataQualityChecker

@pytest.fixture
def mock_dq_checker():
    return DataQualityChecker()

def test_null_check(mock_dq_checker):
    df_clean = pd.DataFrame({"id": [1, 2, 3], "val": ["A", "B", "C"]})
    res_pass = mock_dq_checker.run_null_check(df_clean, ["id", "val"])
    assert res_pass["pass"] is True

    df_dirty = pd.DataFrame({"id": [1, None, 3], "val": ["A", "B", None]})
    res_fail = mock_dq_checker.run_null_check(df_dirty, ["id", "val"])
    assert res_fail["pass"] is False
    assert "id" in res_fail["failed_columns"]
    assert "val" in res_fail["failed_columns"]
    assert res_fail["null_counts"]["id"] == 1
    assert res_fail["null_counts"]["val"] == 1

def test_range_check(mock_dq_checker):
    df = pd.DataFrame({"quantity": [1, 5, 10, 50]})
    res_pass = mock_dq_checker.run_range_check(df, "quantity", 1, 100)
    assert res_pass["pass"] is True

    df_bad = pd.DataFrame({"quantity": [0, 5, 10, 105]})
    res_fail = mock_dq_checker.run_range_check(df_bad, "quantity", 1, 100)
    assert res_fail["pass"] is False
    assert res_fail["out_of_range_count"] == 2

def test_uniqueness_check(mock_dq_checker):
    df_unique = pd.DataFrame({"order_id": ["ORD001", "ORD002", "ORD003"]})
    res_pass = mock_dq_checker.run_uniqueness_check(df_unique, ["order_id"])
    assert res_pass["pass"] is True

    df_dup = pd.DataFrame({"order_id": ["ORD001", "ORD002", "ORD001"]})
    res_fail = mock_dq_checker.run_uniqueness_check(df_dup, ["order_id"])
    assert res_fail["pass"] is False
    assert res_fail["total_records"] == 3
    assert res_fail["unique_records"] == 2

def test_referential_integrity(mock_dq_checker):
    df_child = pd.DataFrame({"customer_id": ["C001", "C002", "C001"]})
    df_parent = pd.DataFrame({"customer_id": ["C001", "C002", "C003"]})
    res_pass = mock_dq_checker.run_referential_integrity(df_child, "customer_id", df_parent, "customer_id")
    assert res_pass["pass"] is True

    df_child_bad = pd.DataFrame({"customer_id": ["C001", "C002", "C999"]})
    res_fail = mock_dq_checker.run_referential_integrity(df_child_bad, "customer_id", df_parent, "customer_id")
    assert res_fail["pass"] is False
    assert res_fail["missing_keys_count"] == 1
