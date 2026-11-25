"""Unit tests for Python DE Modules 01-10."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from modules.m01_variables_and_types import process_transaction_record
from modules.m02_data_structures import deduplicate_and_aggregate_sales
from modules.m03_control_flow_and_functions import apply_transformations
from modules.m08_os_pathlib_subprocess import sanitize_pii
from modules.m10_pandas_and_cleaning import clean_and_aggregate_sales

def test_process_transaction_record():
    raw = {"transaction_id": " txn100 ", "amount": "500.50", "product_category": "Books"}
    cleaned = process_transaction_record(raw)
    assert cleaned["transaction_id"] == "TXN100"
    assert cleaned["amount"] == 500.50
    assert cleaned["category"] == "books"
    assert cleaned["is_high_value"] is True

def test_deduplicate_and_aggregate_sales():
    records = [
        {"transaction_id": "T1", "customer_id": "C1", "amount": 100},
        {"transaction_id": "T1", "customer_id": "C1", "amount": 100},
        {"transaction_id": "T2", "customer_id": "C2", "amount": 200}
    ]
    deduped, spend = deduplicate_and_aggregate_sales(records)
    assert len(deduped) == 2
    assert spend["C1"] == 100.0
    assert spend["C2"] == 200.0

def test_apply_transformations():
    records = [{"val": 10}, {"val": 20}, {"val": 5}]
    res = apply_transformations(
        records,
        filter_fn=lambda r: r["val"] > 8,
        transform_fn=lambda r: {"double_val": r["val"] * 2}
    )
    assert len(res) == 2
    assert res[0]["double_val"] == 20
    assert res[1]["double_val"] == 40

def test_sanitize_pii():
    text = "User email is test@example.com."
    sanitized = sanitize_pii(text)
    assert "[REDACTED_EMAIL]" in sanitized

def test_clean_and_aggregate_sales():
    records = [
        {"status": "COMPLETED", "amount": "100.0", "product_category": "Tech"},
        {"status": "FAILED", "amount": "50.0", "product_category": "Tech"},
        {"status": "COMPLETED", "amount": "200.0", "product_category": "Tech"}
    ]
    agg = clean_and_aggregate_sales(records)
    assert "Tech" in agg
    assert agg["Tech"]["total_sales"] == 300.0
    assert agg["Tech"]["count"] == 2
