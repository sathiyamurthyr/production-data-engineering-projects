"""
================================================================================
MODULE 12: List & Dict Comprehensions
================================================================================
1. EXPLANATION:
Comprehensions provide concise, C-optimized syntax for filtering and transforming collections.
In Python DE, comprehensions outperform explicit `for` loops for in-memory transformations.

2. BUSINESS USE CASE:
Filter valid high-value transaction amounts and map to tax-adjusted dictionaries in a single pass.
"""
from typing import List, Dict, Any

def process_high_value_sales(records: List[Dict[str, Any]], threshold: float = 100.0) -> List[Dict[str, Any]]:
    """Vectorized list comprehension filtering and mapping."""
    return [
        {"id": r["id"], "amount": r["amount"], "tax": round(r["amount"] * 0.05, 2)}
        for r in records
        if r.get("amount", 0.0) >= threshold
    ]

if __name__ == "__main__":
    raw = [{"id": "T1", "amount": 150.0}, {"id": "T2", "amount": 20.0}, {"id": "T3", "amount": 300.0}]
    processed = process_high_value_sales(raw)
    print("High Value Sales:", processed)
