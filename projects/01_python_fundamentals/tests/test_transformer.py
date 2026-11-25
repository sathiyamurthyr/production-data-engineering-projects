"""Unit tests for Pipeline DataTransformer."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src/pipeline"))

from transformer import DataTransformer

def test_transform_sales():
    transformer = DataTransformer()
    valid = [
        {"product_category": "Electronics", "amount": "100.0"},
        {"product_category": "electronics ", "amount": "200.0"},
        {"product_category": "Apparel", "amount": "50.0"}
    ]
    res = transformer.transform_sales(valid)
    assert res["total_revenue"] == 350.0
    assert res["processed_count"] == 3
    assert res["category_summary"]["Electronics"] == 300.0
