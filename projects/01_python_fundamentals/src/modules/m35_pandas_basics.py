"""
================================================================================
MODULE 35: Pandas DataFrames & Vectorized Operations
================================================================================
1. EXPLANATION:
Pandas DataFrames provide high-performance in-memory tabular data manipulation.

2. BUSINESS USE CASE:
Calculate aggregated sales summary statistics.
"""
from typing import List, Dict, Any

def summarize_sales(records: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregate total sales per product category."""
    summary = {}
    for r in records:
        cat = r.get("category", "Unknown")
        amt = float(r.get("amount", 0.0))
        summary[cat] = summary.get(cat, 0.0) + amt
    return summary

if __name__ == "__main__":
    sample = [{"category": "Tech", "amount": 100}, {"category": "Tech", "amount": 200}]
    print("Sales Summary:", summarize_sales(sample))
