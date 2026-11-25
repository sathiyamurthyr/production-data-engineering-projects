"""
================================================================================
MODULE 03: Operators in Data Engineering
================================================================================

1. EXPLANATION:
--------------------------------------------------------------------------------
Operators (arithmetic, comparison, logical, bitwise, membership, identity) perform computations
and condition evaluation. In ETL pipelines, membership operators (`in`) provide O(1) set filtering,
while comparison operators validate thresholds.

2. BUSINESS USE CASE:
--------------------------------------------------------------------------------
Filter valid transactions based on status membership (`status in ALLOWED_STATUSES`),
and verify transaction thresholds (`amount > MIN_THRESHOLD`).

3. PRODUCTION EXAMPLE:
--------------------------------------------------------------------------------
Filters high-value valid transactions using logical and membership operators.

4. EXPECTED OUTPUT:
--------------------------------------------------------------------------------
[INFO] Transaction TXN500 passed validation rules.
"""

from typing import List, Dict, Any

ALLOWED_STATUSES = {"COMPLETED", "SETTLED"}
MIN_TRANSACTION_VALUE = 100.0

def filter_qualifying_transactions(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter records using comparison and membership operators."""
    qualifying = []
    for r in records:
        # Operator checks: membership (in), comparison (>=), identity (is not None)
        if r.get("status") in ALLOWED_STATUSES and r.get("amount") is not None and r["amount"] >= MIN_TRANSACTION_VALUE:
            qualifying.append(r)
    return qualifying

if __name__ == "__main__":
    data = [
        {"txn_id": "TXN500", "status": "COMPLETED", "amount": 250.0},
        {"txn_id": "TXN501", "status": "PENDING", "amount": 500.0},
        {"txn_id": "TXN502", "status": "COMPLETED", "amount": 40.0},
    ]
    res = filter_qualifying_transactions(data)
    print("Qualifying Records:", res)
