"""
================================================================================
MODULE 36: Data Cleaning & Null Value Imputation
================================================================================
1. EXPLANATION:
Data cleaning removes duplicates, handles missing (null) values, and standardizes formats.

2. BUSINESS USE CASE:
Impute missing numerical amounts with default 0.0 and drop invalid rows.
"""
from typing import List, Dict, Any

def clean_dataset(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean data by imputing missing values and filtering bad status."""
    cleaned = []
    for row in raw_data:
        if not row.get("id"):
            continue
        amt = row.get("amount")
        clean_amt = float(amt) if amt is not None else 0.0
        cleaned.append({"id": row["id"], "amount": clean_amt})
    return cleaned
